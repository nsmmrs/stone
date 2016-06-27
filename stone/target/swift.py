from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import os

from contextlib import contextmanager

from stone.data_type import (
    Boolean,
    Bytes,
    DataType,
    Float32,
    Float64,
    Int32,
    Int64,
    List,
    String,
    Timestamp,
    UInt32,
    UInt64,
    Void,
    is_boolean_type,
    is_bytes_type,
    is_list_type,
    is_string_type,
    is_struct_type,
    is_timestamp_type,
    is_union_type,
    is_nullable_type,
    is_numeric_type,
    is_user_defined_type,
    is_void_type,
    unwrap_nullable,
)
from stone.generator import CodeGenerator
from stone.target.swift_helpers import (
    fmt_class,
    fmt_func,
    fmt_obj,
    fmt_type,
    fmt_var,
)


_serial_type_table = {
    Boolean: 'BoolSerializer',
    Bytes: 'NSDataSerializer',
    Float32: 'FloatSerializer',
    Float64: 'DoubleSerializer',
    Int32: 'Int32Serializer',
    Int64: 'Int64Serializer',
    List: 'ArraySerializer',
    String: 'StringSerializer',
    Timestamp: 'NSDateSerializer',
    UInt32: 'UInt32Serializer',
    UInt64: 'UInt64Serializer',
    Void: 'VoidSerializer',
}


class SwiftBaseGenerator(CodeGenerator):
    """Wrapper class over Stone generator for Swift logic."""

    @contextmanager
    def function_block(self, func, args, return_type=None):
        signature = '{}({})'.format(func, args)
        if return_type:
            signature += ' -> {}'.format(return_type)
        with self.block(signature):
            yield

    def _func_args(self, args_list, newlines=False, force_first=False, not_init=False):
        out = []
        first = True
        for k, v in args_list:
            # this is a temporary hack -- injected client-side args
            # do not have a separate field for default value. Right now,
            # default values are stored along with the type, e.g.
            # `Bool = True` is a type, hence this check.
            if first and force_first and '=' not in v:
                k = "{} {}".format(k, k)
            
            if first and v is not None and not_init:
                out.append('{}'.format(v))
            elif v is not None:
                out.append('{}: {}'.format(k, v))
            first = False
        sep = ', '
        if newlines:
            sep += '\n' + self.make_indent()
        return sep.join(out)

    @contextmanager
    def class_block(self, thing, protocols=None):
        protocols = protocols or []
        extensions = []

        if isinstance(thing, DataType):
            name = fmt_class(thing.name)
            if thing.parent_type:
                extensions.append(fmt_type(thing.parent_type))
        else:
            name = thing
        extensions.extend(protocols)

        extend_suffix = ': {}'.format(', '.join(extensions)) if extensions else ''

        with self.block('public class {}{}'.format(name, extend_suffix)):
            yield

    def _struct_init_args(self, data_type, namespace=None):
        args = []
        for field in data_type.all_fields:
            name = fmt_var(field.name)
            value = fmt_type(field.data_type)
            data_type, nullable = unwrap_nullable(field.data_type)

            if field.has_default:
                if is_union_type(data_type):
                    default = '.{}'.format(fmt_class(field.default.tag_name))
                else:
                    default = fmt_obj(field.default)
                value += ' = {}'.format(default)
            elif nullable:
                value += ' = nil'
            arg = (name, value)
            args.append(arg)
        return args

    def _docf(self, tag, val):
        if tag == 'route':
            return fmt_func(val)
        elif tag == 'field':
            if '.' in val:
                cls, field = val.split('.')
                return ('{} in {}'.format(fmt_var(field),
                        fmt_class(cls)))
            else:
                return fmt_var(val)
        elif tag in ('type', 'val', 'link'):
            return val
        else:
            import pdb
            pdb.set_trace()
            return val

def fmt_serial_type(data_type):
    data_type, nullable = unwrap_nullable(data_type)

    if is_user_defined_type(data_type):
        result = '{}.{}Serializer'
        result = result.format(fmt_class(data_type.namespace.name),
                                fmt_class(data_type.name))
    else:
        result = _serial_type_table.get(data_type.__class__, fmt_class(data_type.name))
        
        if is_list_type(data_type):
            result = result + '<{}>'.format(fmt_serial_type(data_type.data_type))        

    return result if not nullable else 'NullableSerializer'


def fmt_serial_obj(data_type):
    data_type, nullable = unwrap_nullable(data_type)

    if is_user_defined_type(data_type):
        result = '{}.{}Serializer()'
        result = result.format(fmt_class(data_type.namespace.name),
                                fmt_class(data_type.name))
    else:
        result = _serial_type_table.get(data_type.__class__, fmt_class(data_type.name))

        if is_list_type(data_type):
            result = result + '({})'.format(fmt_serial_obj(data_type.data_type))
        elif is_timestamp_type(data_type):
            result = result + '("{}")'.format(data_type.format)
        else:
            result = 'Serialization._{}'.format(result)

    return result if not nullable else 'NullableSerializer({})'.format(result)