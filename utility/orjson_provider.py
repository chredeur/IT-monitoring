import dataclasses
import decimal
import uuid
from datetime import date

import orjson
from quart.json.provider import JSONProvider

def _default(obj):
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, (decimal.Decimal, uuid.UUID)):
        return str(obj)
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if hasattr(obj, "__html__"):
        return str(obj.__html__())
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

class OrjsonProvider(JSONProvider):
    mimetype = "application/json"

    def dumps(self, obj, **kwargs) -> str:
        # orjson.dumps → bytes, donc on décode en str
        return orjson.dumps(
            obj,
            default=_default,
            option=orjson.OPT_NON_STR_KEYS | orjson.OPT_INDENT_2,
        ).decode()

    def loads(self, s, **kwargs):
        return orjson.loads(s)

    def response(self, *args, **kwargs):
        obj = self._prepare_response_obj(args, kwargs)
        return self._app.response_class(
            self.dumps(obj) + "\n",
            mimetype=self.mimetype,
        )