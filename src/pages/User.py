import drivebase
from oauth2client.client import AccessTokenRefreshError

class UserHandler(drivebase.BaseDriveHandler):
    """Web handler for the service to read user information."""

    def get(self):
        """Called when HTTP GET requests are received by the web application."""
        # Create a Drive service
        service = self.CreateUserInfo()
        if service is None:
            return
        try:
            result = service.userinfo().get().execute()
            # Generate a JSON response with the file data and return to the client.
            self.RespondJSON(result)
        except AccessTokenRefreshError:
            # Catch AccessTokenRefreshError which occurs when the API client library
            # fails to refresh a token. This occurs, for example, when a refresh token
            # is revoked. When this happens the user is redirected to the
            # Authorization URL.
            self.RedirectAuth()