# Copyright (C) 2016 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
from odoo.addons.account_bank_statement_import_mt940_base.mt940 import (
    MT940, str2amount)


def get_counterpart(transaction, subfield):
    """Get counterpart from transaction.

    Counterpart is often stored in subfield of tag 86. The subfield
    can be 31, 32, 33"""
    if not subfield:
        return  # subfield is empty
    if len(subfield) >= 1 and subfield[0]:
        transaction.update({'account_number': subfield[0]})
    if len(subfield) >= 2 and subfield[1]:
        transaction.update({'partner_name': subfield[1]})
    if len(subfield) >= 3 and subfield[2]:
        # Holds the partner VAT number
        pass


def get_subfields(data, codewords):
    """Return dictionary with value array for each codeword in data.

    For instance:
    data =
        000+20TRANSACTIONTYPE+30BANKTRANSACTIONNUMBER+31PARTNERBANKACCOUNT
        +32PARTNER+33CUI/CNPTIN
        +23TRANSACTIONMESSAGE1+24TRANSACTIONMESSAGE2
        +25TRANSACTIONMESSAGE3+26TRANSACTIONMESSAGE4
        +27TRANSACTIONMESSAGE5
        +61PARTNERADDRESS1+62PARTNERADDRESS2
    codewords = ['20', '23', '24', '25', '26', '27',
                 '30', '31', '32', '33', '61', '62']
    !!! NOT ALL CODEWORDS ARE PRESENT !!!
    Then return subfields = {
        '20': [TRANSACTIONTYPE],
        '30': [BANKTRANSACTIONNUMBER],
        '31': [PARTNERBANKACCOUNT],
        '32': [PARTNER],
        '33': [TIN],
        '23': [TRANSACTIONMESSAGE1],
        '24': [TRANSACTIONMESSAGE2],
        '25': [TRANSACTIONMESSAGE3],
        '26': [TRANSACTIONMESSAGE4],
        '27': [TRANSACTIONMESSAGE5],
        '61': [PARTNERADDRESS1],
        '62': [PARTNERADDRESS2],
    }
    """
    subfields = {}
    current_codeword = None
    for word in data.split('+'):
        if not word and not current_codeword:
            continue
        if word[:2] in codewords:
            current_codeword = word[:2]
            subfields[current_codeword] = [word[2:]]
            continue
        if current_codeword in subfields:
            subfields[current_codeword].append(word[2:])
    return subfields


def handle_common_subfields(transaction, subfields):
    """Deal with common functionality for tag 86 subfields."""
    # Get counterpart from 31, 32 or 33 subfields:
    counterpart_fields = []
    for counterpart_field in ['31', '32', '33']:
        if counterpart_field in subfields:
            new_value = subfields[counterpart_field][0].replace('CUI/CNP', '')
            counterpart_fields.append(new_value)
        else:
            counterpart_fields.append('')
    if counterpart_fields:
        get_counterpart(transaction, counterpart_fields)
    # REMI: Remitter information (text entered by other party on trans.):
    if not transaction.get('name'):
        transaction['name'] = ''
    for counterpart_field in ['23', '24', '25', '26', '27']:
        if counterpart_field in subfields:
            transaction['name'] += (
                '/'.join(x for x in subfields[counterpart_field] if x))
    # Get transaction reference subfield (might vary):
    if transaction.get('ref') in subfields:
        transaction['ref'] = ''.join(subfields[transaction['ref']])


class MT940Parser(MT940):
    """Parser for ing MT940 bank statement import files."""

    tag_61_regex = re.compile(
        r'^(?P<date>\d{6})(?P<line_date>\d{0,4})'
        r'(?P<sign>[CD])(?P<amount>\d+,\d{2})N(?P<type>.{3})'
        r'(?P<reference>\w{1,50})'
    )

    def __init__(self):
        """Initialize parser - override at least header_regex."""
        super(MT940Parser, self).__init__()
        self.mt940_type = 'BRD'
        self.header_lines = 0
        self.header_regex = '^:20:'  # Start of relevant data

    def is_mt940_statement(self, line):
        """determine if line is the start of a statement"""
        if not bool(line.startswith(':20:')):
            raise ValueError(
                'The pre processed match %s does not seem to be a'
                ' valid %s MT940 format bank statement. Every statement'
                ' should start be a dict starting with {4:..' % line
            )

    def pre_process_data(self, data):
        matches = []
        self.is_mt940(line=data)
        data = data.replace(
            '-}', '}').replace('}{', '}\r\n{').replace('\r\n', '\n')
        if data.startswith(':20:'):
            for statement in data.split(':20:'):
                match = ':20:' + statement
                matches.append(match)
            return matches
        return super(MT940Parser, self).pre_process_data(data)

    def handle_tag_25(self, data):
        """Local bank account information."""
        data = data.replace('.', '').strip()
        self.account_number = data

    def handle_tag_28(self, data):
        """Number of BRD bank statement."""
        self.current_statement['name'] = data.replace('.', '').strip()

    def handle_tag_61(self, data):
        """get transaction values"""
        super(MT940Parser, self).handle_tag_61(data)
        re_61 = self.tag_61_regex.match(data)
        if not re_61:
            raise ValueError("Cannot parse %s" % data)
        parsed_data = re_61.groupdict()
        self.current_transaction['amount'] = (
            str2amount(parsed_data['sign'], parsed_data['amount']))
        self.current_transaction['note'] = parsed_data['reference']

    def handle_tag_86(self, data):
        """Parse 86 tag containing reference data."""
        if not self.current_transaction:
            return
        codewords = ['20', '23', '24', '25', '26', '27',
                     '30', '31', '32', '33', '61', '62']
        subfields = get_subfields(data, codewords)
        transaction = self.current_transaction
        # If we have no subfields, set message to whole of data passed:
        if not subfields:
            transaction.message = data
        else:
            handle_common_subfields(transaction, subfields)
        # Prevent handling tag 86 later for non transaction details:
        self.current_transaction = None
