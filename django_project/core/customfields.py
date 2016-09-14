import sys
import binascii
import string
import warnings
import six
import django
from Crypto import Random
from Crypto.Random import random
from django import forms
from django.conf import settings
from django.core import exceptions
from django.db import models
from django.db.models import fields
from django.db.models.fields.related import OneToOneField
from django.utils.encoding import smart_str, force_unicode
from django.utils.translation import ugettext as _
from django.core.exceptions import ImproperlyConfigured



try:
    from keyczar import keyczar
except ImportError:
    raise ImportError('Using an encrypted field requires the Keyczar module. '
                      'You can obtain Keyczar from http://www.keyczar.org/.')


class EncryptionWarning(RuntimeWarning):
    pass


class BigIntegerField(fields.IntegerField):
    def db_type(self, connection):
        if 'mysql' in settings.DATABASES['default']['ENGINE']:
            return "bigint"
        elif 'oracle' in settings.DATABASES['default']['ENGINE']:
            return "NUMBER(19)"
        elif 'postgres' in settings.DATABASES['default']['ENGINE']:
            return "bigint"
        elif 'sqlite3' in settings.DATABASES['default']['ENGINE']:
            return super(BigIntegerField, self).db_type(connection)
        else:
            raise NotImplemented
    
    def get_internal_type(self):
        return "BigIntegerField"
    
    def to_python(self, value):
        if value is None:
            return value
        try:
            return long(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                _("This value must be a long integer."))


class BigAutoField(fields.AutoField):
    def db_type(self, connection):
        if 'mysql' in settings.DATABASES['default']['ENGINE']:
            return "bigint AUTO_INCREMENT"
        elif 'oracle' in settings.DATABASES['default']['ENGINE']:
            return "NUMBER(19)"
        elif 'postgres' in settings.DATABASES['default']['ENGINE']:
            return "bigserial"
        elif 'sqlite3' in settings.DATABASES['default']['ENGINE']:
            return super(BigAutoField, self).db_type(connection)
        else:
            raise NotImplemented
 
    def get_internal_type(self):
        return "BigAutoField"
    
    def to_python(self, value):
        if value is None:
            return value
        try:
            return long(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                _("This value must be a long integer."))
 
class BigForeignKey(fields.related.ForeignKey):
    
    def db_type(self, connection):
        rel_field = self.rel.get_related_field()
        # next lines are the "bad tooth" in the original code:
        if (isinstance(rel_field, BigAutoField) or
                (not connection.features.related_fields_match_type and
                isinstance(rel_field, BigIntegerField))):
            # because it continues here in the django code:
            # return IntegerField().db_type()
            # thereby fixing any AutoField as IntegerField
            return BigIntegerField().db_type(connection)
        return rel_field.db_type(connection)


class BigOneToOneField(BigForeignKey, OneToOneField):
    """
    If you use subclass model, you might need to name 
    the `ptr` field explicitly. This is the field type you 
    might want to use. Here is an example: 
    
    class Base(models.Model):
        title = models.CharField(max_length=40, verbose_name='Title')

    class Concrete(Base):
        base_ptr = fields.BigOneToOneField(Base)
        ext = models.CharField(max_length=12, null=True, verbose_name='Ext')
    """
    pass


"""
Copyright (c) 2008, Alexander Artemenko
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY Alexander Artemenko ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <copyright holder> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

class BaseEncryptedField(models.Field):
    prefix = 'enc_str:::'

    def __init__(self, *args, **kwargs):
        if not hasattr(settings, 'ENCRYPTED_FIELD_KEYS_DIR'):
            raise ImproperlyConfigured('You must set the settings.ENCRYPTED_FIELD_KEYS_DIR '
                                       'setting to your Keyczar keys directory.')
        crypt_class = self.get_crypt_class()
        self.crypt = crypt_class.Read(settings.ENCRYPTED_FIELD_KEYS_DIR)

        # Encrypted size is larger than unencrypted
        self.unencrypted_length = max_length = kwargs.get('max_length', None)
        if max_length:
            kwargs['max_length'] = self.calculate_crypt_max_length(max_length)

        super(BaseEncryptedField, self).__init__(*args, **kwargs)

    def calculate_crypt_max_length(self, unencrypted_length):
        # TODO: Re-examine if this logic will actually make a large-enough
        # max-length for unicode strings that have non-ascii characters in them.
        # For PostGreSQL we might as well always use textfield since there is little
        # difference (except for length checking) between varchar and text in PG.
        return len(self.prefix) + len(self.crypt.Encrypt('x' * unencrypted_length))

    def get_crypt_class(self):
        """
        Get the Keyczar class to use.
        The class can be customized with the ENCRYPTED_FIELD_MODE setting. By default,
        this setting is DECRYPT_AND_ENCRYPT. Set this to ENCRYPT to disable decryption.
        This is necessary if you are only providing public keys to Keyczar.
        Returns:
            keyczar.Encrypter if ENCRYPTED_FIELD_MODE is ENCRYPT.
            keyczar.Crypter if ENCRYPTED_FIELD_MODE is DECRYPT_AND_ENCRYPT.
        Override this method to customize the type of Keyczar class returned.
        """

        crypt_type = getattr(settings, 'ENCRYPTED_FIELD_MODE', 'DECRYPT_AND_ENCRYPT')
        if crypt_type == 'ENCRYPT':
            crypt_class_name = 'Encrypter'
        elif crypt_type == 'DECRYPT_AND_ENCRYPT':
            crypt_class_name = 'Crypter'
        else:
            raise ImproperlyConfigured(
                'ENCRYPTED_FIELD_MODE must be either DECRYPT_AND_ENCRYPT '
                'or ENCRYPT, not %s.' % crypt_type)
        return getattr(keyczar, crypt_class_name)

    def to_python(self, value):
        if isinstance(self.crypt.primary_key, keyczar.keys.RsaPublicKey):
            retval = value
        elif value and (value.startswith(self.prefix)):
            if hasattr(self.crypt, 'Decrypt'):
                retval = self.crypt.Decrypt(value[len(self.prefix):])
                if sys.version_info < (3,):
                    if retval:
                        retval = retval.decode('utf-8')
            else:
                retval = value
        else:
            retval = value
        return retval

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        if value and not value.startswith(self.prefix):
            # We need to encode a unicode string into a byte string, first.
            # keyczar expects a bytestring, not a unicode string.
            if sys.version_info < (3,):
                if type(value) == six.types.UnicodeType:
                    value = value.encode('utf-8')
            # Truncated encrypted content is unreadable,
            # so truncate before encryption
            max_length = self.unencrypted_length
            if max_length and len(value) > max_length:
                warnings.warn("Truncating field %s from %d to %d bytes" % (
                    self.name, len(value), max_length), EncryptionWarning
                )
                value = value[:max_length]

            value = self.prefix + self.crypt.Encrypt(value)
        return value

    def deconstruct(self):
        name, path, args, kwargs = super(BaseEncryptedField, self).deconstruct()
        kwargs['max_length'] = self.unencrypted_length
        return name, path, args, kwargs


if django.VERSION < (1, 8):
    EncryptedFieldBase = six.with_metaclass(models.SubfieldBase,
                                            BaseEncryptedField)
else:
    EncryptedFieldBase = BaseEncryptedField


class EncryptedTextField(EncryptedFieldBase):
    def get_internal_type(self):
        return 'TextField'

    def formfield(self, **kwargs):
        defaults = {'widget': forms.Textarea}
        defaults.update(kwargs)
        return super(EncryptedTextField, self).formfield(**defaults)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)


class EncryptedCharField(EncryptedFieldBase):
    def __init__(self, *args, **kwargs):
        super(EncryptedCharField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"

    def formfield(self, **kwargs):
        defaults = {'max_length': self.max_length}
        defaults.update(kwargs)
        return super(EncryptedCharField, self).formfield(**defaults)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.CharField"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)
