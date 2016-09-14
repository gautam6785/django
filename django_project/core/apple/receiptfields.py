import receipt_field_value_types

NO_VALUE_TYPE = receipt_field_value_types.AbstractAppReceiptFieldValueType()
DATETIME_VALUE_TYPE = receipt_field_value_types.AppReceiptFieldIa5ToDatetimeValueType()
IA5_STRING_VALUE_TYPE = receipt_field_value_types.AppReceiptFieldIa5StringValueType()
INTEGER_VALUE_TYPE = receipt_field_value_types.AppReceiptFieldIntegerValueType()
OCTET_VALUE_TYPE = receipt_field_value_types.AppReceiptFieldOctetValueType()
UTF8_STRING_VALUE_TYPE = receipt_field_value_types.AppReceiptFieldUtf8StringValueType()

class ReceiptField():
  def __init__(self, field_name, field_type):
    self.field_name = field_name
    self.field_type = field_type

  def name(self):
    return self.field_name

  def value(self, raw_value):
    return self.field_type.coerce(raw_value)

# App receipt fields
APPLICATION_VERSION = ReceiptField('application_version', UTF8_STRING_VALUE_TYPE)
BUNDLE_ID = ReceiptField('bundle_id', UTF8_STRING_VALUE_TYPE)
EXPIRES_DATE = ReceiptField('expires_date', DATETIME_VALUE_TYPE)
IN_APP_PURCHASE = ReceiptField('in_app', NO_VALUE_TYPE)
OPAQUE_VALUE = ReceiptField('opaque_value', OCTET_VALUE_TYPE)
ORIGINAL_APPLICATION_VERSION = ReceiptField('original_application_version', UTF8_STRING_VALUE_TYPE)
ORIGINAL_PURCHASE_DATE_UNDOCUMENTED = ReceiptField('original_purchase_date', DATETIME_VALUE_TYPE)
SHA1_HASH = ReceiptField('sha1_hash', OCTET_VALUE_TYPE)

# Map from receipt field type to field instance.
FIELD_MAP = {
  2: BUNDLE_ID,
  3: APPLICATION_VERSION,
  4: OPAQUE_VALUE,
  5: SHA1_HASH,
  17: IN_APP_PURCHASE,
  18: ORIGINAL_PURCHASE_DATE_UNDOCUMENTED,
  19: ORIGINAL_APPLICATION_VERSION,
  21: EXPIRES_DATE,
}

# An informational map containing unused, undocumented receipt fields.
UNUSED_FIELD_MAP = {
  0: ReceiptField('environment', UTF8_STRING_VALUE_TYPE),
  1: ReceiptField('app_item_id', INTEGER_VALUE_TYPE),
  8: ReceiptField('unknown_8', DATETIME_VALUE_TYPE),
  9: ReceiptField('unknown_9', INTEGER_VALUE_TYPE),
  10: ReceiptField('unknown_10', IA5_STRING_VALUE_TYPE),
  11: ReceiptField('unknown_11', INTEGER_VALUE_TYPE),
  12: ReceiptField('unknown_12', DATETIME_VALUE_TYPE),
  13: ReceiptField('unknown_13', INTEGER_VALUE_TYPE),
  14: ReceiptField('unknown_14', INTEGER_VALUE_TYPE),
  15: ReceiptField('unknown_15', INTEGER_VALUE_TYPE),
  16: ReceiptField('unknown_16', INTEGER_VALUE_TYPE),
  20: ReceiptField('unknown_20', UTF8_STRING_VALUE_TYPE),
  25: ReceiptField('unknown_25', INTEGER_VALUE_TYPE),
}
