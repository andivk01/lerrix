class Video:
    def __init__(self, original_name=None, location=None):
        self.original_name = original_name
        self.location = location
        self.formatted_name = self.formatted_name()
        self.extension = self.extension()
    
    def formatted_name(self):
        if self.original_name.startswith("202"): # 2022-10-04_11-00-06.mkv
            return self.original_name.replace("-", " ")

        if len(self.original_name.split("-")) > 1: 
            datetime = self.original_name.split("-")[1]
            date = datetime[:8]
            time = datetime[9:]
            extension = self.original_name.split(".")[-1]
            return f"{date}_{time}.{extension}"
        return self.original_name
    
    def extension(self):
        return self.original_name.split(".")[-1]

    def __repr__(self):
        return f"{self.original_name} -> {self.formatted_name}"
    
    def to_dict(self):
        return {
            "original_name": self.original_name,
            "location": self.location,
            "formatted_name": self.formatted_name,
            "extension": self.extension
        }