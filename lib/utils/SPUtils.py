import datetime

def format_filename(filename):
    filename = filename.replace("-", "") # 2022-10-04_11-00-16.mkv -> 20221004_110016.mkv
    extension = filename.split(".")[-1]

    date_start_idx = filename.find("202")
    date_end_idx = date_start_idx + 8
    time_start_idx = date_end_idx + 1
    time_end_idx = time_start_idx + 6
    try:
        date = datetime.strptime(filename[date_start_idx:date_end_idx], "%Y%m%d")
        time = datetime.strptime(filename[time_start_idx:time_end_idx], "%H%M%S")
        return f"{date.strftime('%d-%m-%Y')} {time.strftime('%H.%M.%S')}.{extension}"
    except Exception as e: # TODO: make this more specific?
        print(f"Exception while formatting name: {filename}\n{e}") # TODO FILENAME IS MODIFIED
        return None