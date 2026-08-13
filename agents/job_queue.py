from utils.sheet_io import (
    get_pending_job,
    update_status,
    update_raw_file_id,
    update_finished_file_id,
    update_clip_metadata
)

def fetch_job(sheet, spreadsheet_id, range_name):
    return get_pending_job(sheet, spreadsheet_id, range_name)

def mark_started(sheet, spreadsheet_id, row):
    update_status(sheet, spreadsheet_id, row, "processing")

def mark_done(sheet, spreadsheet_id, row, raw_id, finished_id, title=None, description=None, viral_score=None):
    update_raw_file_id(sheet, spreadsheet_id, row, raw_id)
    update_finished_file_id(sheet, spreadsheet_id, row, finished_id)

    # Update clip metadata from Gemini AI (if available)
    if title and description and viral_score:
        update_clip_metadata(sheet, spreadsheet_id, row, title, description, viral_score)

    update_status(sheet, spreadsheet_id, row, "done")
