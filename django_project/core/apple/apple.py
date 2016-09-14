import logging

from core.apple import receiptfields
from iap_local_receipt.iap_pkcs7_verifier import PKCS7Verifier
from iap_local_receipt.iap_receipt import IAPReceipt
from iap_local_receipt.iap_receipt_parser import AppReceipt, IAPReceiptParser
from iap_local_receipt.iap_receipt_verifier import IAPReceiptVerifier
from pyasn1.codec.der.decoder import decode


logger = logging.getLogger(__name__)

APPLE_ROOT_CA_CERT = """
-----BEGIN CERTIFICATE-----
MIIEuzCCA6OgAwIBAgIBAjANBgkqhkiG9w0BAQUFADBiMQswCQYDVQQGEwJVUzET
MBEGA1UEChMKQXBwbGUgSW5jLjEmMCQGA1UECxMdQXBwbGUgQ2VydGlmaWNhdGlv
biBBdXRob3JpdHkxFjAUBgNVBAMTDUFwcGxlIFJvb3QgQ0EwHhcNMDYwNDI1MjE0
MDM2WhcNMzUwMjA5MjE0MDM2WjBiMQswCQYDVQQGEwJVUzETMBEGA1UEChMKQXBw
bGUgSW5jLjEmMCQGA1UECxMdQXBwbGUgQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkx
FjAUBgNVBAMTDUFwcGxlIFJvb3QgQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw
ggEKAoIBAQDkkakJH5HbHkdQ6wXtXnmELes2oldMVeyLGYne+Uts9QerIjAC6Bg+
+FAJ039BqJj50cpmnCRrEdCju+QbKsMflZ56DKRHi1vUFjczy8QPTc4UadHJGXL1
XQ7Vf1+b8iUDulWPTV0N8WQ1IxVLFVkds5T39pyez1C6wVhQZ48ItCD3y6wsIG9w
tj8BMIy3Q88PnT3zK0koGsj+zrW5DtleHNbLPbU6rfQPDgCSC7EhFi501TwN22IW
q6NxkkdTVcGvL0Gz+PvjcM3mo0xFfh9Ma1CWQYnEdGILEINBhzOKgbEwWOxaBDKM
aLOPHd5lc/9nXmW8Sdh2nzMUZaF3lMktAgMBAAGjggF6MIIBdjAOBgNVHQ8BAf8E
BAMCAQYwDwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQUK9BpR5R2Cf70a40uQKb3
R01/CF4wHwYDVR0jBBgwFoAUK9BpR5R2Cf70a40uQKb3R01/CF4wggERBgNVHSAE
ggEIMIIBBDCCAQAGCSqGSIb3Y2QFATCB8jAqBggrBgEFBQcCARYeaHR0cHM6Ly93
d3cuYXBwbGUuY29tL2FwcGxlY2EvMIHDBggrBgEFBQcCAjCBthqBs1JlbGlhbmNl
IG9uIHRoaXMgY2VydGlmaWNhdGUgYnkgYW55IHBhcnR5IGFzc3VtZXMgYWNjZXB0
YW5jZSBvZiB0aGUgdGhlbiBhcHBsaWNhYmxlIHN0YW5kYXJkIHRlcm1zIGFuZCBj
b25kaXRpb25zIG9mIHVzZSwgY2VydGlmaWNhdGUgcG9saWN5IGFuZCBjZXJ0aWZp
Y2F0aW9uIHByYWN0aWNlIHN0YXRlbWVudHMuMA0GCSqGSIb3DQEBBQUAA4IBAQBc
NplMLXi37Yyb3PN3m/J20ncwT8EfhYOFG5k9RzfyqZtAjizUsZAS2L70c5vu0mQP
y3lPNNiiPvl4/2vIB+x9OYOLUyDTOMSxv5pPCmv/K/xZpwUJfBdAVhEedNO3iyM7
R6PVbyTi69G3cN8PReEnyvFteO3ntRcXqNx+IjXKJdXZD9Zr1KIkIxH3oayPc4Fg
xhtbCS+SsvhESPBgOJ4V9T0mZyCKM2r3DYLP3uujL/lTaltkwGMzd/c6ByxW69oP
IQ7aunMZT7XZNn/Bh1XZp5m5MkL72NVxnn6hUrcbvZNCJBIqxw8dtk2cXmPIS4AX
UKqK1drk/NAJBzewdXUh
-----END CERTIFICATE-----
"""


class ReceiptParser(IAPReceiptParser):
  def __init__(self, parse_undocumented_fields):
    super(ReceiptParser, self).__init__()
    self.parseUndocumentedFields = parse_undocumented_fields

  def parse_app_receipt(self, receipt_der):
    """
    Parse an App Receipt ASN.1 blob, and return an
    IAPReceipt object.
    """
    self.last_receipt_der = receipt_der
    self.last_receipt = None

    # Decode raw data as AppReceipt
    receipt, unprocessed = decode(receipt_der, asn1Spec=AppReceipt())

    # Parse top-level receipt fields
    app_receipt = {}
    iap_receipts = []

    # Convert raw fields into Python dict values
    for field in receipt:
      receiptField = receiptfields.FIELD_MAP.get(field['type'], None)
      if receiptField:
        fieldValue = field['value']
        if receiptField == receiptfields.IN_APP_PURCHASE:
          iap_receipts.append(self.parse_iap_receipt(fieldValue))
        else:
          app_receipt[receiptField.name()] = receiptField.value(fieldValue)
          if receiptField == receiptfields.BUNDLE_ID:  # Needed for hash, do not translate
            app_receipt['raw_' + receiptField.name()] = fieldValue.asOctets()
      elif self.parseUndocumentedFields:
        receiptField = receiptfields.UNUSED_FIELD_MAP.get(field['type'], None)
        if receiptField:
          fieldValue = field['value']
          try:
            app_receipt[receiptField.name()] = receiptField.value(fieldValue)
          except Exception as e:
            logger.info('Could not parse iOS receipt field type %s' % str(field['type']))
            continue

    in_app = receiptfields.IN_APP_PURCHASE.name()
    app_receipt[in_app] = iap_receipts
    self.last_receipt = IAPReceipt(app_receipt)
    return self.last_receipt


class ReceiptVerifier(IAPReceiptVerifier):
    """
    Convenience class that houses a receipt parser and verifier
    for situations where many receipts need to be parsed, and
    the overhead of repeatedly parsing the CA cert is unwanted.
    """
    def __init__(self, ca_cert=None, ca_cert_string=None, parse_undocumented_fields=False):
        self._receipt_parser = ReceiptParser(parse_undocumented_fields)
        self._verifier = PKCS7Verifier(root_ca_cert_file=ca_cert,
            root_ca_cert_string=ca_cert_string)
        if not (ca_cert or ca_cert_string):
          raise Exception("Need one of ca_cert or ca_cert_string")
