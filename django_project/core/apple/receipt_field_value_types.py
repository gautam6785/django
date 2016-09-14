from iap_local_receipt import rfc3339
from pyasn1.codec.der.decoder import decode
from pyasn1.type import char, univ


class AbstractAppReceiptFieldValueType():
  def coerce(self, raw_value):
    raise NotImplementedError('Implementation not defined for abstract base class.')


class AppReceiptFieldIa5StringValueType(AbstractAppReceiptFieldValueType):
  def coerce(self, raw_value):
    value, unprocessed = decode(raw_value, asn1Spec=char.IA5String())
    return str(value)


class AppReceiptFieldIa5ToDatetimeValueType(AbstractAppReceiptFieldValueType):
  def coerce(self, raw_value):
    value, unprocessed = decode(raw_value, asn1Spec=char.IA5String())
    strValue = str(value)
    return rfc3339.parse_datetime(strValue) if strValue else None


class AppReceiptFieldIntegerValueType(AbstractAppReceiptFieldValueType):
  def coerce(self, raw_value):
    value, unprocessed = decode(raw_value, asn1Spec=univ.Integer())
    return int(value)


class AppReceiptFieldOctetValueType(AbstractAppReceiptFieldValueType):
  def coerce(self, raw_value):
    return raw_value.asOctets()


class AppReceiptFieldUtf8StringValueType(AbstractAppReceiptFieldValueType):
  def coerce(self, raw_value):
    value, unprocessed = decode(raw_value, asn1Spec=char.UTF8String())
    return str(value)
