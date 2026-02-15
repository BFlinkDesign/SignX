"""
Outlook COM automation script to sample bid request emails.
Connects to Outlook Classic via win32com.client and enumerates folders under Inbox/BID REQUEST/.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import win32com.client
    import pythoncom
except ImportError:
    print("ERROR: win32com not available. Install with: pip install pywin32")
    sys.exit(1)


def get_folder_recursive(parent_folder, path_parts):
    """Navigate to a folder using path components."""
    if not path_parts:
        return parent_folder

    try:
        next_folder = parent_folder.Folders[path_parts[0]]
        return get_folder_recursive(next_folder, path_parts[1:])
    except Exception as e:
        raise Exception(f"Failed to navigate to {'/'.join(path_parts)}: {e}")


def get_all_subfolders(folder):
    """Recursively get all subfolders."""
    subfolders = []
    try:
        for subfolder in folder.Folders:
            subfolders.append(subfolder)
            subfolders.extend(get_all_subfolders(subfolder))
    except Exception as e:
        print(f"Warning: Failed to enumerate subfolders in {folder.Name}: {e}")
    return subfolders


def sample_folder_emails(folder, max_samples=3):
    """Sample most recent emails from a folder."""
    samples = []

    try:
        items = folder.Items

        # Skip empty folders
        if items.Count == 0:
            return samples

        items.Sort("[ReceivedTime]", True)  # Sort descending (most recent first)

        count = 0
        for item in items:
            if count >= max_samples:
                break

            try:
                # Only process MailItems
                if item.Class != 43:  # olMail = 43
                    continue

                # Get attachment info
                attachment_names = []
                try:
                    for attachment in item.Attachments:
                        attachment_names.append(attachment.FileName)
                except Exception as e:
                    print(f"  Warning: Failed to get attachments: {e}")

                # Get body preview (plain text, first 2000 chars)
                body_preview = ""
                try:
                    body = item.Body or ""
                    body_preview = body[:2000]
                except Exception as e:
                    print(f"  Warning: Failed to get body: {e}")

                # Convert ReceivedTime to ISO string
                received_iso = ""
                try:
                    if hasattr(item, 'ReceivedTime') and item.ReceivedTime:
                        received_iso = item.ReceivedTime.isoformat()
                except Exception as e:
                    print(f"  Warning: Failed to convert ReceivedTime: {e}")

                sample = {
                    "subject": item.Subject or "",
                    "from": item.SenderName or "",
                    "received": received_iso,
                    "body_preview": body_preview,
                    "has_attachments": len(attachment_names) > 0,
                    "attachment_names": attachment_names
                }

                samples.append(sample)
                count += 1

            except Exception as e:
                print(f"  Warning: Failed to process email in {folder.Name}: {e}")
                continue

    except Exception as e:
        print(f"Warning: Failed to sample emails from {folder.Name}: {e}")

    return samples


def main():
    output_path = Path(r"C:\Users\Brady.EAGLE\Desktop\SignX\SignX-Intake\recon\email-samples.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "folders": [],
        "discovered_at": datetime.now().isoformat()
    }

    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        print(f"Attempt {attempt}/{max_attempts}: Connecting to Outlook...")

        try:
            # Initialize COM
            pythoncom.CoInitialize()

            # Connect to Outlook
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")

            # Navigate to Inbox/BID REQUEST/
            print("Navigating to Inbox/BID REQUEST/...")
            inbox = namespace.GetDefaultFolder(6)  # olFolderInbox = 6
            bid_request_folder = inbox.Folders["BID REQUEST"]

            print(f"Found BID REQUEST folder: {bid_request_folder.Name}")

            # Get all subfolders recursively
            print("Enumerating all subfolders...")
            all_subfolders = get_all_subfolders(bid_request_folder)

            print(f"Found {len(all_subfolders)} subfolders total")

            # Process each subfolder
            for i, subfolder in enumerate(all_subfolders, 1):
                try:
                    folder_path = f"Inbox/BID REQUEST/{subfolder.Name}"
                    email_count = subfolder.Items.Count

                    print(f"[{i}/{len(all_subfolders)}] Processing: {folder_path} ({email_count} emails)", flush=True)

                    # Skip empty folders
                    if email_count == 0:
                        print(f"  Skipping empty folder", flush=True)
                        continue

                    # Sample most recent emails
                    samples = sample_folder_emails(subfolder, max_samples=3)
                    print(f"  Sampled {len(samples)} emails", flush=True)

                    folder_data = {
                        "folder_name": subfolder.Name,
                        "folder_path": folder_path,
                        "email_count": email_count,
                        "samples": samples
                    }

                    result["folders"].append(folder_data)

                except Exception as e:
                    print(f"  ERROR: Failed to process subfolder {subfolder.Name}: {e}")
                    continue

            # Success - write output
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"\nSUCCESS: Sampled {len(result['folders'])} folders")
            print(f"Output written to: {output_path}")

            pythoncom.CoUninitialize()
            sys.exit(0)

        except Exception as e:
            error_msg = f"Attempt {attempt} failed: {e}"
            print(f"ERROR: {error_msg}")

            if attempt >= max_attempts:
                # Save error info to JSON
                result["error"] = error_msg
                result["folders"] = []

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                print(f"Max attempts reached. Error info saved to: {output_path}")

                try:
                    pythoncom.CoUninitialize()
                except:
                    pass

                sys.exit(1)

            print("Retrying...")

            try:
                pythoncom.CoUninitialize()
            except:
                pass


if __name__ == "__main__":
    main()
