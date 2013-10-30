import drivebase
from apiclient import errors

import jinja2
import os

# Jinja is the templating tool we use
JINJA_ENVIRONMENT = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
        extensions=['jinja2.ext.autoescape'])


class TransferOwnershipHandler(drivebase.BaseDriveHandler):
    """Web handler for the main page.

    Handles requests and returns the user interface for Open With and Create
    cases. Responsible for parsing the state provided from the Drive UI and acting
    appropriately.
    """


    def insert_permission(self, service, file_id, value, perm_type, role):
        """Insert a new permission.
        
        Args:
        service: Drive API service instance.
        file_id: ID of the file to insert permission for.
        value: User or group e-mail address, domain name or None for 'default'
             type.
        perm_type: The value 'user', 'group', 'domain' or 'default'.
        role: The value 'owner', 'writer' or 'reader'.
        Returns:
        The inserted permission if successful, None otherwise.
        """
        new_permission = {
            'value': value,
            'type': perm_type,
            'role': role
        }
        try:
            return service.permissions().insert(
                fileId=file_id, body=new_permission).execute()
        except errors.HttpError, error:
            print 'An error occurred: %s' % error
            return None
    
    def update_permission(self, service, file_id, permission_id, new_role):
        """Update a permission's role.
        
        Args:
        service: Drive API service instance.
        file_id: ID of the file to update permission for.
        permission_id: ID of the permission to update.
        new_role: The value 'owner', 'writer' or 'reader'.
        
        Returns:
        The updated permission if successful, None otherwise.
        """
        try:
        # First retrieve the permission from the API.
            permission = service.permissions().get(
                fileId=file_id, permissionId=permission_id).execute()
                
            permission['role'] = new_role
            return service.permissions().update(
                fileId=file_id, permissionId=permission_id, body=permission).execute()
        except errors.HttpError, error:
            print 'An error occurred: %s' % error
            return None
        
    def retrieve_all_files(self, service):
        """Retrieve a list of File resources.
    
        Args:
            service: Drive API service instance.
        Returns:
            List of File resources.
        """
        result = []
        page_token = None
        while True:
            try:
                param = {}
                if page_token:
                    param['pageToken'] = page_token
                files = service.files().list(**param).execute()
    
                result.extend(files['items'])
                page_token = files.get('nextPageToken')
                if not page_token:
                    break
            except errors.HttpError, error:
                print 'An error occurred: %s' % error
                break
        return result
    
    def traverse(self, service, folder_id, recursion_depth):
        #self.response.out.write("Traversing " + str(folder_id) + "<br />")
        if service.files().get(fileId=folder_id).execute()['mimeType'] != 'application/vnd.google-apps.folder':
            return None
        if recursion_depth <= 0:
            return []
        files = []
        param = {}
        children = service.children().list(
            folderId=folder_id, **param).execute()
        for child in children['items']:
            file = service.files().get(fileId=child['id']).execute()
            file['ownerNameString'] = ",".join(file['ownerNames'])
            if file['mimeType'] == 'application/vnd.google-apps.folder':
                files.append(file)
                files.extend(self.traverse(service, file['id'], recursion_depth - 1))
            else:
                files += [file]
        return files

    def get(self):
        """Handle GET for Create New and Open With.

        This creates an authorized client, and checks whether a resource id has
        been passed or not. If a resource ID has been passed, this is the Open
        With use-case, otherwise it is the Create New use-case.
        """
        # Generate a state instance for the request, this includes the action, and
        # the file id(s) that have been sent from the Drive user interface.
        drive_state = drivebase.DriveState.FromRequest(self.request)
        template_values = {
                'action': drive_state.action,
                'ids': drive_state.ids,
        }
        
        if drive_state.action == 'open' and len(drive_state.ids) > 0:
            template_values['code'] = self.request.get('code')
        
        # Fetch the credentials by extracting an OAuth 2.0 authorization code from
        # the request URL. If the code is not present, redirect to the OAuth 2.0
        # authorization URL.
        creds = self.GetCodeCredentials()
        if not creds:
            return self.RedirectAuth()
        
        new_owner = self.request.get('new_owner')
        

        # Create a Drive service
        service = drivebase.CreateService('drive', 'v2', creds)
        if len(drive_state.ids) > 0:
            # Do something
            
            if not new_owner:
                template = JINJA_ENVIRONMENT.get_template('error.html')
                template_values = { 'error': 'New owner not defined'}
                self.response.write(template.render(template_values))
                return
            if not new_owner.endswith('rit.edu'):
                template = JINJA_ENVIRONMENT.get_template('error.html')
                template_values = { 'error': 'Illegal new owner.  Must end in rit.edu\n\nGiven: ' + new_owner}
                self.response.write(template.render(template_values))
                return
            
            if self.is_folder(service, drive_state.ids[0]):
                files = self.traverse(service, drive_state.ids[0], 5)
                for file in files:
                    self.insert_permission(service, file['id'], new_owner, 'user', 'owner')
                template_values = { 'files': files}
                template = JINJA_ENVIRONMENT.get_template('index.html')
                self.response.write(template.render(template_values))
            else:
                self.response.out.write("Not a folder\n")
        else:
            template = JINJA_ENVIRONMENT.get_template('auth.html')
            self.response.out.write(template.render())
            
            #files = self.retrieve_all_files(service)
            #files = self.traverse(service, "0BwyAT8fk8FVDQU5wSnp1WUVua28", 4)
            #self.response.write("<br />".join(files))
            #template_values = { 'files': files}
            #template = JINJA_ENVIRONMENT.get_template('index.html')
            #self.response.write(template.render(template_values))
            
        # Extract the numerical portion of the client_id from the stored value in
        # the OAuth flow. You could also store this value as a separate variable
        # somewhere.
        # template_values['client_id'] = self.CreateOAuthFlow().client_id.split('.')[0].split('-')[0]
        # self.RenderTemplate(template_values)

    def RenderTemplate(self, vals):
        """Render a named template in a context."""
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(self.INDEX_HTML)
        
    def is_folder(self, service, file_id):
            """Print a file's metadata.

            Args:
                service: Drive API service instance.
                file_id: ID of the file to print metadata for.
            """
            try:
                file = service.files().get(fileId=file_id).execute()

                return 'application/vnd.google-apps.folder' == file['mimeType']
            except errors.HttpError, error:
                print 'An error occurred: %s' % error
                return False
        
    def print_files_in_folder(self, service, folder_id):
        """Print files belonging to a folder.

        Args:
        service: Drive API service instance.
        folder_id: ID of the folder to print files from.
        """
        page_token = None
        while True:
            try:
                param = {}
                if page_token:
                    param['pageToken'] = page_token
                children = service.children().list(
                    folderId=folder_id, **param).execute()
    
                for child in children.get('items', []):
                    print 'File Id: %s' % child['id']
                page_token = children.get('nextPageToken')
                if not page_token:
                    break
            except errors.HttpError, error:
                print 'An error occurred: %s' % error
                break