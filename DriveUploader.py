from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pickle
from threading import Thread





class DriveUploader:

    
    @staticmethod
    def _load_cached_items(filepath='items.cache'):
        items = []
        with open(filepath, 'rb') as fp:
            items = pickle.load(fp)
        return items

    @staticmethod
    def _save_cached_items(items, filepath='items.cache'):
        try:
            with open(filepath, 'wb') as fp:
                pickle.dump(items, fp)
        except Exception:
            print('Could not save cached items')



    def __init__(self, settings_file='settings.yaml'):
        gauth = GoogleAuth()
        self.drive = GoogleDrive(gauth)
        refresh_thread = Thread(target=self.refresh_items)
        try:
            self.items = DriveUploader._load_cached_items()
            refresh_thread.start()
        except FileNotFoundError:
            refresh_thread.start()
            refresh_thread.join()


    def refresh_items(self):
        self.items = [{
            'id'            : item['id'],
            'title'         : item['title'],
            'parent'        : item['parents'][0]['id'] if len(item['parents']) else '/'
        } for item in self.drive.ListFile({'q': 'trashed=false'}).GetList()]
        DriveUploader._save_cached_items(self.items)
 
    def upload(self, local_filepath, remote_dir_id, force=False):
        # Check if file already exists and apply some logic
        filename = local_filepath.split('/')[-1]
        if any( item['parent']+item['title'] == remote_dir_id+filename for item in self.items ) and not force:
            raise FileExistsError("File already present in remote directory")
        self.unsafe_uploader(local_filepath, remote_dir_id)


    def unsafe_upload(self, local_filepath, remote_dir_id):
        filename = local_filepath.split('/')[-1]
        rfile = self.drive.CreateFile({
            'title' :   filename,
            'parents' : [{
                'id' : remote_dir_id
            }]
        })
        rfile.SetContentFile(local_filepath)
        rfile.upload()



if __name__ == '__main__' :
    du = DriveUploader()
    res = input(">")
    print(res)



