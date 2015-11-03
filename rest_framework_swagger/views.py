import urlparse
from django.views.generic import View
from django.utils.safestring import mark_safe
from django.shortcuts import render_to_response, RequestContext
from django.core.exceptions import PermissionDenied

from rest_framework2.views import Response
from rest_framework_swagger.urlparser import UrlParser
from rest_framework_swagger.apidocview import APIDocView
from rest_framework_swagger.docgenerator import DocumentationGenerator

from rest_framework_swagger import SWAGGER_SETTINGS


class SwaggerUIView(View):

    def get(self, request, *args, **kwargs):

        if not self.has_permission(request):
            raise PermissionDenied()

        template_name = "rest_framework_swagger/index.html"
        data = {
            'settings': {
                'discovery_url': "%sapi-docs/" % request.build_absolute_uri(),
                'api_key': SWAGGER_SETTINGS.get('api_key', ''),
                'enabled_methods': mark_safe(SWAGGER_SETTINGS.get('enabled_methods'))
            }
        }
        response = render_to_response(template_name, RequestContext(request, data))

        return response

    def has_permission(self, request):
        if SWAGGER_SETTINGS.get('is_superuser') and not request.user.is_superuser:
            return False

        if SWAGGER_SETTINGS.get('is_authenticated') and not request.user.is_authenticated():
            return False

        return True


class SwaggerResourcesView(APIDocView):

    def get(self, request):
        apis = []
        parsed = urlparse.urlparse(self.host)
        host_with_path = '%s://%s%s' % (parsed.scheme, parsed.netloc, parsed.path)
        self.request_path = parsed.path

        resources = self.get_resources()

        for path in resources:
            apis.append({
                'path': "/%s" % path,
            })

        parsed = urlparse.urlparse(self.host)
        return Response({
            'apiVersion': SWAGGER_SETTINGS.get('api_version', ''),
            'swaggerVersion': '1.2.4',
            'basePath': host_with_path,
            'apis': apis
        })

    def get_resources(self):
        urlparser = UrlParser()
        apis = urlparser.get_apis(exclude_namespaces=SWAGGER_SETTINGS.get('exclude_namespaces'))
        # Swagger urlparser has bug that causes exclude_namespaces to not work in some cases
        # In our case we dont want to include all urls from all modules to same documentation
        # so instead we check that the apis url (current url) can be found from the endpoints url.
        # If not then it belogn to another module and we dont include it to documentation.
        filtered_apis = []
        p = self.request_path.replace('api-docs/', '')
        for endpoint in apis:
            try:
                str(endpoint['path']).index(p)
                filtered_apis.append(endpoint)
            except ValueError:
                pass

        return urlparser.get_top_level_apis(filtered_apis)

class SwaggerApiView(APIDocView):

    def get(self, request, path):
        apis = self.get_api_for_resource(path)
        generator = DocumentationGenerator()

        return Response({
            'apis': generator.generate(apis),
            'models': generator.get_models(apis),
            'basePath': self.api_full_uri,
        })

    def get_api_for_resource(self, filter_path):
        urlparser = UrlParser()
        return urlparser.get_apis(filter_path=filter_path)
