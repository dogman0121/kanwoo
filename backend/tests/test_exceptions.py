from flask import Flask
from marshmallow import Schema, fields

from kanwoo.exceptions import setup_exceptions


def test_unhandled_schema_validation_error_returns_bad_request():
    class RequestSchema(Schema):
        name = fields.String(required=True)

    app = Flask(__name__)
    setup_exceptions(app)

    @app.get("/")
    def validate_request():
        return RequestSchema().load({})

    response = app.test_client().get("/")

    assert response.status_code == 400
    assert response.json == {
        "error": {"code": "bad_request", "detail": {"name": ["Missing data for required field."]}}
    }
