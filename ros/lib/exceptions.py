class HTTPError(Exception):
    def __init__(self, status_code, message=""):
        """
        Raise this exception to return an http response indicating an error.
        This is a boilerplate exception that was originally from Crane project.
        :param status_code: HTTP status code. It's a good idea to get this straight
                            from httplib, such as httplib.NOT_FOUND
        :type  status_code: int
        :param message:     optional error message to be put in the response
                            body. If not supplied, the default message for the
                            status code will be used.
        """
        super(HTTPError, self).__init__()
        self.message = message
        self.status_code = status_code


class IllegalHttpMethodError(ValueError):
    def __init__(self, message):
        """
        Raise this exception if we detect illegal HTTP method
        """
        super().__init__()
        self.message = message


class RBACDenied(Exception):
    def __init__(self, message):
        """
        Raise this exception if the inventory service reports that you do not
        have rbac permission to access the service
        """
        super().__init__()
        self.message = message


class ItemNotReturned(Exception):
    def __init__(self, message):
        """
        Raise this exception if an item was not returned by inventory service
        """
        super().__init__()
        self.message = message


class ServiceError(Exception):
    def __init__(self, message):
        """
        Raise this exception if the inventory service is not reachable or does
        not provide a valid response
        """
        super().__init__()
        self.message = message
