import os
from concurrent.futures import ThreadPoolExecutor
from lib.download.Downloader import Downloader
from lib.utils.SPUtils import format_filename, handle_exc

class SP_Downloader(Downloader):

    def __init__(self, tmp_directory, chunk_length=300, 
                chunk_threads=1, download_history=None,
                format_filename_func=format_filename,
                download_extension=None, download_threads=1):

        super().__init__(tmp_directory, chunk_length, chunk_threads)
        self.download_history = download_history
        self.format_filename_func = format_filename_func
        self.download_extension = download_extension
        self.download_threads = download_threads
    
    def download_spvideo(self, video, file_prefix, output_dir):
        formatted_title = self.format_filename_func(video["filename"])
        formatted_title = formatted_title[:formatted_title.rfind(".")]
        extension = video["filename"].split(".")[-1]
        if self.download_extension is not None:
            extension = self.download_extension

        output_file = os.path.join(output_dir, f"{file_prefix}{formatted_title}.{extension}")

        return self.download(video["sources"], output_file)

    def download_spvideos(self, videos, file_prefix, output_dir):
        with ThreadPoolExecutor(max_workers=self.download_threads) as executor:
            for video in videos:
                download_spvideo_func = handle_exc()(self.download_spvideo)
                executor.submit(download_spvideo_func, video, file_prefix, output_dir)

