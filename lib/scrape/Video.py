from datetime import datetime

class Video:
    def __init__(self, original_name=None, location=None, formatted_name=None):
        self.original_name = original_name
        self.location = location
        self.extension = Video.extension(self.original_name)
        if formatted_name is not None:
            self.formatted_name = formatted_name
        else:
            self.formatted_name = Video.formatted_name(self.original_name)
    
    def formatted_name(original_name):
        original = original_name.replace("-", "") # 2022-10-04_11-00-16.mkv -> 20221004_110016.mkv
        extension = Video.extension(original_name)
        try:
            date_start_idx = original.find("202")
            date_end_idx = date_start_idx + 8
            time_start_idx = date_end_idx + 1
            time_end_idx = time_start_idx + 6
            date = datetime.strptime(original[date_start_idx:date_end_idx], "%Y%m%d")
            time = datetime.strptime(original[time_start_idx:time_end_idx], "%H%M%S")
            return f"{date.strftime('%d-%m-%Y')} {time.strftime('%H.%M.%S')}.{extension}"
        except Exception as e:
            print(f"Exception while formatting name: {original_name}\n{e}")
            return original_name
    
    def extension(original_name):
        return original_name.split(".")[-1]

    def __repr__(self):
        return f"{self.original_name} -> {self.formatted_name}"
    
    def to_dict(self):
        return {
            "original_name": self.original_name,
            "location": self.location,
            "formatted_name": self.formatted_name,
            "extension": self.extension
        }