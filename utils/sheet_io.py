import uuid
from datetime import datetime

def get_pending_job(sheet, SPREADSHEET_ID, RANGE_NAME):
    """
    Get pending job from Google Sheets

    Expected columns:
    A: job_id
    B: youtube_url
    C: raw_file_id (optional)
    D: finished_file_id (optional)
    E: status
    """
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()

    rows = result.get("values", [])

    # Debug: print semua rows
    print(f"📊 Found {len(rows)} rows in spreadsheet")

    if not rows:
        return None, None

    for idx, row in enumerate(rows, start=2):
        # Debug: print setiap row
        print(f"🔍 Row {idx}: {len(row)} columns -> {row}")

        # Check if row has at least 5 columns (job_id, youtube_url, raw_id, finished_id, status)
        if len(row) < 5:
            print(f"   → Skipped: Not enough columns (need 5, got {len(row)})")
            continue

        # Extract status (column E = index 4)
        status = row[4].strip().lower() if len(row) > 4 else ""
        print(f"   → job_id='{row[0]}', status='{status}'")

        if status != "pending":
            print(f"   → Skipped: Status is '{status}', not 'pending'")
            continue

        job = {
            "row": idx,
            "job_id": row[0],
            "youtube_url": row[1]
        }
        print(f"✅ Found pending job: {job}")
        return idx, job

    print("⚠️  No pending jobs found")
    return None, None


def update_status(sheet, SPREADSHEET_ID, row, status):
    """Update status di kolom E"""
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Jobs!E{row}",
        valueInputOption="RAW",
        body={"values": [[status]]}
    ).execute()
    print(f"📝 Updated row {row} status to: {status}")


def update_raw_file_id(sheet, SPREADSHEET_ID, row, file_id):
    """Update raw_file_id di kolom C"""
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Jobs!C{row}",
        valueInputOption="RAW",
        body={"values": [[file_id]]}
    ).execute()
    print(f"📝 Updated row {row} raw_file_id to: {file_id}")


def update_finished_file_id(sheet, SPREADSHEET_ID, row, file_id):
    """Update finished_file_id di kolom D"""
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Jobs!D{row}",
        valueInputOption="RAW",
        body={"values": [[file_id]]}
    ).execute()
    print(f"📝 Updated row {row} finished_file_id to: {file_id}")


def update_clip_metadata(sheet, SPREADSHEET_ID, row, title, description, viral_score):
    """
    Update clip metadata (title, description, viral_score) from Gemini AI

    Columns:
    F: title (Gemini-generated)
    G: description (Gemini-generated)
    H: viral_score (1-10)
    """
    # Update title (column F)
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Jobs!F{row}",
        valueInputOption="RAW",
        body={"values": [[title]]}
    ).execute()

    # Update description (column G)
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Jobs!G{row}",
        valueInputOption="RAW",
        body={"values": [[description]]}
    ).execute()

    # Update viral_score (column H)
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Jobs!H{row}",
        valueInputOption="RAW",
        body={"values": [[viral_score]]}
    ).execute()

    print(f"📝 Updated row {row} clip metadata:")
    print(f"   Title: {title}")
    print(f"   Description: {description[:50]}..." if len(description) > 50 else f"   Description: {description}")
    print(f"   Viral Score: {viral_score}/10")


def append_clip_to_sheet(sheet, SPREADSHEET_ID, parent_job_id, drive_file_id, title, description, tags, target_channel):
    try:
        clip_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # --- PERBAIKAN DI SINI ---
        # Jika tags berupa list, gabungkan jadi string koma (misal: "saham, investasi, uang")
        # Jika tags None, ubah jadi string kosong
        if isinstance(tags, list):
            tags_formatted = ", ".join(tags) 
        else:
            tags_formatted = str(tags) if tags else ""
        # -------------------------

        values = [[
            clip_id,
            parent_job_id,
            drive_file_id,
            title,
            description,
            tags_formatted, # <--- Gunakan variabel yang sudah diformat string
            target_channel,
            "READY",
            timestamp
        ]]
        
        # Append ke sheet 'Clips'
        body = {'values': values}
        range_name = 'Clips!A2:I'  # A-I adalah 9 kolom
        
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        print(f"📋 Added clip to sheet: {title} (ID: {clip_id})")
        return result
        
    except Exception as e:
        print(f"❌ Failed to add clip to sheet: {e}")
        raise


def mark_job_complete(sheet, SPREADSHEET_ID, row, raw_fid, fin_fid):
    """
    Menandai job utama sebagai selesai di sheet 'Jobs'.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # --- LANGKAH 1: Update File ID dan Status (Kolom C, D, E) ---
        # Range C sampai E (3 Kolom)
        job_range = f"Jobs!C{row}:E{row}"
        
        # PERBAIKAN: Pastikan list hanya berisi 3 item!
        # [raw_file_id, output_file_id, status]
        # Hapus 'timestamp' dari list ini agar tidak meluap ke kolom F
        values = [[raw_fid, fin_fid, "done"]] 
        
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=job_range,
            valueInputOption='RAW',
            body={'values': values}
        ).execute()

        # --- LANGKAH 2: Update Timestamp (Kolom L) ---
        # Sesuai header CSV Anda, 'updated_at' ada di kolom L (urutan ke-12)
        time_range = f"Jobs!L{row}"
        
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=time_range,
            valueInputOption='RAW',
            body={'values': [[timestamp]]}
        ).execute()
        
        print(f"✅ Marked job at row {row} as DONE (Updated timestamp in Col L)")
        
    except Exception as e:
        print(f"❌ Failed to mark job complete: {e}")
        raise