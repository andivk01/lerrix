from datetime import datetime
import traceback

def format_filename(filename):
    filename_no_dash = filename.replace("-", "") # 2022-10-04_11-00-16.mkv -> 20221004_110016.mkv

    date_start_idx = filename_no_dash.find("202")
    date_end_idx = date_start_idx + 8
    time_start_idx = date_end_idx + 1
    time_end_idx = time_start_idx + 6
    try:
        extension = filename.split(".")[-1]
        date = datetime.strptime(filename_no_dash[date_start_idx:date_end_idx], "%Y%m%d")
        time = datetime.strptime(filename_no_dash[time_start_idx:time_end_idx], "%H%M%S")
        return f"{date.strftime('%d-%m-%Y')} {time.strftime('%H.%M.%S')}.{extension}"
    except Exception as e: # TODO: make this more specific?
        print(f"Exception while formatting name: {filename}\n{e}")
        return filename

def handle_exc(handler_func=None): # TODO
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if handler_func is not None:
                    handler_func(e)
                else:
                    traceback.print_exc()
        return wrapper
    return decorator