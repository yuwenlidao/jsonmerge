# vim:ts=4 sw=4 expandtab softtabstop=4
from jsonmerge.exceptions import HeadInstanceError, SchemaError
from jsonmerge.jsonvalue import JSONValue

class Descender(object):
    """Base class for descender classes.

    Descenders are similar to merge strategies, except that they only handle
    recursion into deeper schema structures and don't touch instances.
    """
    def descend_instance(self, walk, schema, base, head, meta):
        return None

    def descend_schema(self, walk, schema, meta):
        return None

class Ref(Descender):
    def __init__(self):
        self.refs_descended = set('#')

    def descend_instance(self, walk, schema, base, head, meta):
        ref = schema.val.get("$ref")
        if ref is None:
            return None

        with walk.resolver.resolving(ref) as resolved:
            return walk.descend(JSONValue(resolved, ref), base, head, meta)

    def descend_schema(self, walk, schema, meta):
        ref = schema.val.get("$ref")
        if ref is None:
            return None

        if ref in self.refs_descended:
            return schema

        if walk.resolver.is_remote_ref(ref):
            return schema

        self.refs_descended.add(ref)

        with walk.resolver.resolving(ref) as resolved:

            rinstance = JSONValue(resolved, ref)
            if not walk.is_type(rinstance, 'object'):
                raise SchemaError("'$ref' does not point to an object")

            result = walk.descend(rinstance, meta)

            resolved.clear()
            resolved.update(result.val)

        return schema

class OneOf(Descender):
    def descend_instance(self, walk, schema, base, head, meta):
        one_of = schema.get("oneOf")
        if one_of.is_undef():
            return None

        valid = []

        def is_valid(v, schema):
            if v.is_undef():
                return True
            else:
                return not list(walk.merger.validator.iter_errors(v.val, schema))

        for i, subschema in enumerate(one_of.val):
            base_valid = is_valid(base, subschema)
            head_valid = is_valid(head, subschema)

            if base_valid and head_valid:
                valid.append(i)

        if len(valid) == 0:
            raise HeadInstanceError("No element of 'oneOf' validates both base and head")

        if len(valid) > 1:
            raise HeadInstanceError("Multiple elements of 'oneOf' validate")

        i = valid[0]
        return walk.descend(one_of[i], base, head, meta)

    def descend_schema(self, walk, schema, meta):
        one_of = schema.get("oneOf")
        if one_of.is_undef():
            return None

        for i in range(len(one_of.val)):
            one_of.val[i] = walk.descend(one_of[i], meta).val

        return schema

class AnyOfAllOf(Descender):
    def descend(self, schema):
        for forbidden in ("allOf", "anyOf"):
            if forbidden in schema.val:
                raise SchemaError("Can't descend to 'allOf' and 'anyOf' keywords")
        return None

    def descend_instance(self, walk, schema, base, head, meta):
        return self.descend(schema)

    def descend_schema(self, walk, schema, meta):
        return self.descend(schema)
