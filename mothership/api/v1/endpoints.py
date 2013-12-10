from flask import request
from flask import url_for
from flask import current_app

from api import api  # Circular, but safe

from .decorators import limit
from .serializers import registry
from .helpers import serialize_data_to_response
from .helpers import is_serializer_registered
from .helpers import SERIALIZER_TYPES

from .resources.contact import ContactResource
from .resources.group import GroupResource

# TODO should we use
# http://flask-restful.readthedocs.org/en/latest/quickstart.html
contacts = ContactResource()
groups = GroupResource()


def _create_serialized_response(response_data):
    """ Convenience method to serialize a python dict to
        json or msgpack based on request's `format` argument
    """
    # if request includes format argument, get it.
    serializer_slug = request.args.get('format')

    if serializer_slug is not None:
        # `format` is not required, so if an unregisterd format is
        # requested then this will raise an exception and return a 422.
        # Also, even if headers indicate a different content type,
        # the explicitly passed format arg will be preferred.
        return serialize_data_to_response(data=response_data,
                                          serializer_slug=serializer_slug)

    # if format is not explicitly given as an arg, look at request headers
    mimes = request.accept_mimetypes  # shorthand to prevent lines > 79 chars
    best = mimes.best_match(SERIALIZER_TYPES)

    # Why check if msgpack has a higher quality than default and not just
    # go with the best match? Because some browsers accept on */* and
    # we don't want to deliver msgpack to anything not asking for it.
    # TODO if request header accepts msgpack but serializer is not registered,
    # we will silently return json instead of an error
    if is_serializer_registered('msgpack'):
        if (best == registry.get('msgpack').content_type) \
                and (mimes[best] > mimes[registry.default.content_type]):
            serializer_slug = best

    return serialize_data_to_response(data=response_data,
                                      serializer_slug=serializer_slug)


@api.route('/contact', methods=['GET'])
@limit(max_requests=10, period=60, by="ip")
def get_contact():
    result = contacts.get()
    return _create_serialized_response({'contacts': result})


@api.route('/group/list', methods=['GET'])
@limit(max_requests=10, period=60, by="ip")
def list_groups():
    result = groups.list()
    return _create_serialized_response({'groups': result})


@api.route('/', methods=['GET'])
@limit(max_requests=10, period=60, by="ip")
def list_resources():
    result = {}
    # TODO this seems like a hacky way to do this..
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint.startswith(api.name):
            result.update({rule.endpoint.split('.')[-1]:
                           {"href": url_for(rule.endpoint, _external=True),
                            "methods": list(rule.methods)}})
    return _create_serialized_response({'resources': result})
