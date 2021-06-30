class RBACDenied(Exception):
    def __init__(self, message):
        """
        Raise this exception if the inventory service reports that you do not
        have rbac permission to access the service
        """
        super().__init__()
        self.message = message
