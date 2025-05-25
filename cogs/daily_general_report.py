# ======================================
#  Imports
# ======================================
import os
import csv
import random
import time
import json
import hashlib
import unicodedata
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiohttp
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Local modules
# from users_access_token import API_ACCESS_TOKENS
from utils.ad_account_ids import BM1, BM3, BM4
from utils.body_requests import generate_ringba_insights

# ======================================
#  Constants
# ======================================
load_dotenv()

# Discord bot configuration
DISCORD_TOKEN     = os.getenv("DISCORD_TOKEN")
PREFIX            = os.getenv("PREFIX", "/")
APPLICATION_ID    = os.getenv("APPLICATION_ID")

# Ringba API credentials
RINGBA_ACCOUNT_ID = os.getenv("RINGBA_ACCOUNT_ID")
RINGBA_API_TOKEN  = os.getenv("RINGBA_API_TOKEN")

# Google Apps Script and Sheets configuration
SCOPES                  = [
    "https://www.googleapis.com/auth/script.projects",
    "https://www.googleapis.com/auth/spreadsheets"
]
SPREADSHEET_ID          = os.getenv("SPREADSHEET_ID")
SCRIPT_ID               = os.getenv("SCRIPT_ID")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_TOKEN_FILE       = os.getenv("GOOGLE_TOKEN_FILE", "token.json")

# File system settings
INSIGHTS_FOLDER         = os.getenv("INSIGHTS_FOLDER", "insights")
RINGBA_INSIGHTS_FOLDER  = os.getenv("RINGBA_INSIGHTS_FOLDER", "ringba_insights")

# Google Sheets ranges and sheets
RANGE_NAME_META         = os.getenv("META_RANGE_NAME", "test meta!A1")
RANGE_NAME_RINGBA       = os.getenv("RINGBA_RANGE_NAME", "test ringba!A1")
META_SHEET_NAME         = os.getenv("META_SHEET_NAME", "test meta")
RINGBA_SHEET_NAME       = os.getenv("RINGBA_SHEET_NAME", "test ringba")

# Facebook Business API tokens (loaded from .env)
LI1_TOKEN = os.getenv("LI1_TOKEN")
LI2_TOKEN = os.getenv("LI2_TOKEN")
LI3_TOKEN = os.getenv("LI3_TOKEN")
LI4_TOKEN = os.getenv("LI4_TOKEN")

# List them in order so we can index into it
ACCESS_TOKENS = [LI1_TOKEN, LI2_TOKEN, LI3_TOKEN, LI4_TOKEN]

# Random identifier for temporary files
random_number = random.randint(100000, 999999)


class DailyGeneralReport(commands.Cog):
    """
    Cog for generating daily advertising insights reports
    from Meta and Ringba, saving as CSV, and appending to Google Sheets.
    """

    def __init__(self, client: commands.Bot):
        self.client = client
        self.hash_set = set()  # store hashes of existing rows
        self.new_values_meta = []
        self.new_values_ringba = []

    # ======================================
    #  Generic Methods
    # ======================================
    async def fetch_insights(self, since, until, access_token, adaccounts):
        """Fetch insights in a background thread."""
        try:
            return await asyncio.to_thread(
                self.get_insights, since, until, access_token, adaccounts
            )
        except Exception as e:
            print(f"Error fetching insights: {e}")
            return []

    async def send_private_message(self, user_id: str, message: str):
        """Send a direct message to a user by ID."""
        try:
            user = await self.client.fetch_user(user_id)
            await user.send(message)
        except Exception as e:
            print(f"Failed to send DM to {user_id}: {e}")

    # ======================================
    #  External Clients
    # ======================================
    def get_insights(self, since, until, access_token, adaccounts):
        """Retrieve adset insights from Meta API asynchronously."""
        fields = [
            'spend', 'cpm', 'cpc', 'adset_name',
            'cost_per_inline_link_click', 'inline_link_click_ctr',
            'inline_link_clicks', 'account_name',
            'video_avg_time_watched_actions'
        ]
        insights_data = []

        for account_id in adaccounts:
            print(f"Processing Meta account ID: {account_id}")
            params = {
                'time_range': {'since': since, 'until': until},
                'filtering': [], 'level': 'adset', 'breakdowns': []
            }
            try:
                FacebookAdsApi.init(access_token=access_token)
                job = AdAccount(account_id).get_insights_async(fields=fields, params=params)
                async_job = job.api_get()
                while async_job['async_status'] != 'Job Completed':
                    async_job = job.api_get()
                results = job.get_result()

                for item in results:
                    publisher = (
                        'BM1' if account_id in BM1 else
                        'BM3' if account_id in BM3 else
                        'BM4' if account_id in BM4 else ''
                    )
                    avg_playtime = ''
                    video_stats = item.get('video_avg_time_watched_actions', [])
                    if video_stats:
                        avg_playtime = video_stats[0].get('value', '')

                    insights_data.append({
                        'date_start': item['date_start'],
                        'date_stop': item['date_stop'],
                        'account_name': item['account_name'],
                        'publisher': publisher,
                        'adset_name': item['adset_name'],
                        'cpc_link': item.get('cost_per_inline_link_click', ''),
                        'ctr_link': item.get('inline_link_click_ctr', ''),
                        'inline_link_click': item.get('inline_link_clicks', ''),
                        'cpm': item.get('cpm', ''),
                        'spend': item['spend'],
                        'avg_playtime': avg_playtime,
                    })
            except Exception as e:
                print(f"Meta API error for {account_id}: {e}")

        return insights_data

    async def run_apps_script(self, sheet_name, date_start):
        """Execute Google Apps Script function to delete rows by date."""
        creds = None
        if os.path.exists(GOOGLE_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                await asyncio.to_thread(creds.refresh, Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, SCOPES)
                creds = await asyncio.to_thread(flow.run_local_server, port=0)
            with open(GOOGLE_TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())

        try:
            service = build('script', 'v1', credentials=creds)
            request = {"function": "deleteRowsByDate", "parameters": [date_start, sheet_name]}
            response = await asyncio.to_thread(
                service.scripts().run(body=request, scriptId=SCRIPT_ID).execute
            )
            print("Apps Script executed successfully", response)
            return response
        except Exception as e:
            print(f"Apps Script error: {e}")
            return None

    async def post_ringba_insights(self, session, body):
        """Send insights request to Ringba API and save JSON response."""
        url = f"https://api.ringba.com/v2/{RINGBA_ACCOUNT_ID}/insights"
        headers = {"Authorization": f"Token {RINGBA_API_TOKEN}"}
        async with session.post(url, json=body, headers=headers) as resp:
            data = await resp.json()
            with open('response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print("Ringba response JSON saved")
            return data

    # ======================================
    #  Utilities
    # ======================================
    def clean_string(self, text):
        """Remove accents and replace spaces with underscores."""
        return ''.join(c for c in unicodedata.normalize('NFD', text)
                       if unicodedata.category(c) != 'Mn').replace(' ', '_')

    def time_to_seconds(self, time_str):
        """Convert HH:MM:SS to total seconds."""
        try:
            t = datetime.strptime(time_str, '%H:%M:%S')
            return t.hour * 3600 + t.minute * 60 + t.second
        except ValueError:
            return 0

    def truncate(self, number, decimals=0):
        """Truncate float to specified decimals."""
        factor = 10 ** decimals
        return int(number * factor) / factor

    def save_insights_to_csv_meta(self, data, since, file_name="general_report.csv"):
        """Save Meta insights to CSV file."""
        os.makedirs(INSIGHTS_FOLDER, exist_ok=True)
        path = os.path.join(INSIGHTS_FOLDER, file_name)
        if not data:
            print("No Meta data to save.")
            return None
        cols = ['date_start','date_stop','account_name','publisher','adset_name',
                'cpc_link','ctr_link','inline_link_click','cpm','spend','avg_playtime']
        with open(path, 'w', newline='', encoding='utf-8') as csvf:
            w = csv.writer(csvf)
            w.writerow(cols)
            for row in data:
                row['adset_name'] = self.clean_string(row['adset_name'])
                w.writerow([row.get(c, '-no value-') for c in cols])
        print(f"Meta CSV generated at {path}")
        return path

    def save_insights_to_csv_ringba(self, response_json, since, file_name="ringba_insights_report.csv"):
        """Save Ringba insights records to CSV."""
        os.makedirs(RINGBA_INSIGHTS_FOLDER, exist_ok=True)
        path = os.path.join(RINGBA_INSIGHTS_FOLDER, file_name)
        records = response_json.get('report', {}).get('records', [])
        if not records:
            print("No Ringba records to save.")
            return None
        cols = ["date_start","date_stop","callCount","liveCallCount","endedCalls","connectedCallCount",
                "payoutCount","convertedCalls","nonConnectedCallCount","duplicateCalls",
                "blockedCalls","incompleteCalls","earningsPerCallGross","conversionAmount",
                "payoutAmount","profitGross","profitMarginGross","convertedPercent",
                "callLengthInSeconds","avgHandleTime","totalCost","publisherName",
                "tag:User:sub5","campaignName"]
        with open(path, 'w', newline='', encoding='utf-8') as csvf:
            w = csv.writer(csvf)
            w.writerow(cols)
            for rec in records:
                rec['callLengthInSeconds'] = self.time_to_seconds(rec.get('callLengthInSeconds', '00:00:00'))
                rec['avgHandleTime'] = self.time_to_seconds(rec.get('avgHandleTime', '00:00:00'))
                rec['earningsPerCallGross'] = self.truncate(float(rec.get('earningsPerCallGross',0)),3)
                rec['tag:User:sub5'] = self.clean_string(rec.get('tag:User:sub5',''))
                rec['date_start'] = since
                rec['date_stop'] = since
                w.writerow([rec.get(col, '-no value-') for col in cols])
        print(f"Ringba CSV generated at {path}")
        return path

    async def get_existing_data(self, service):
        """Fetch existing rows from Google Sheets."""
        res = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME_META+':Z'
        ).execute()
        return set(tuple(r) for r in res.get('values', []))

    async def get_existing_data_ringba(self, service):
        """Fetch existing Ringba rows from Google Sheets."""
        res = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME_RINGBA+':Z'
        ).execute()
        return set(tuple(r) for r in res.get('values', []))

    # ======================================
    #  Flows
    # ======================================
    async def update_google_sheets(self, file_path):
        """Append new Meta CSV rows to Google Sheets."""
        creds = None
        if os.path.exists(GOOGLE_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    GOOGLE_CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(GOOGLE_TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())

        try:
            service = build('sheets', 'v4', credentials=creds)
            existing = await self.get_existing_data(service)
            new_rows = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for r in reader:
                    if tuple(r) not in existing:
                        new_rows.append(r)
            if new_rows:
                service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME_META,
                    valueInputOption='RAW', insertDataOption='INSERT_ROWS', body={'values': new_rows}
                ).execute()
                print(f"Appended {len(new_rows)} new Meta rows.")
                self.new_values_meta = new_rows
        except HttpError as e:
            print(f"Error updating Meta sheets: {e}")

    async def update_google_sheets_ringba(self, file_path):
        """Append new Ringba CSV rows to Google Sheets."""
        creds = None
        if os.path.exists(GOOGLE_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    GOOGLE_CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(GOOGLE_TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())

        try:
            service = build('sheets', 'v4', credentials=creds)
            existing = await self.get_existing_data_ringba(service)
            new_rows = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for r in reader:
                    if tuple(r) not in existing:
                        new_rows.append(r)
            if new_rows:
                service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME_RINGBA,
                    valueInputOption='RAW', insertDataOption='INSERT_ROWS', body={'values': new_rows}
                ).execute()
                print(f"Appended {len(new_rows)} new Ringba rows.")
                self.new_values_ringba = new_rows
        except HttpError as e:
            print(f"Error updating Ringba sheets: {e}")

    async def ringba_insights(self, interaction: discord.Interaction, since: str, defer_response=True):
        """Execute the Ringba insights flow and notify user."""
        if defer_response:
            await interaction.response.defer(ephemeral=True)
        tomorrow = datetime.strptime(since, "%Y-%m-%d") + timedelta(days=1)
        start = f"{since}T05:00:00Z"
        end = tomorrow.strftime("%Y-%m-%dT04:59:59Z")
        body = generate_ringba_insights(start_date=start, end_date=end)
        async with aiohttp.ClientSession() as session:
            data = await self.post_ringba_insights(session, body)
            if data.get('isSuccessful'):
                path = self.save_insights_to_csv_ringba(data, since)
                if path:
                    await self.update_google_sheets_ringba(path)
                    await interaction.followup.send(f"Ringba insights saved to {path}.", ephemeral=True)
                else:
                    await interaction.followup.send("Failed to save Ringba CSV.", ephemeral=True)
            else:
                await interaction.followup.send("Ringba API request unsuccessful.", ephemeral=True)

    # ======================================
    #  Commands
    # ======================================
    @discord.app_commands.command(
        name="daily-general-report",
        description="Generate daily Meta and Ringba insights reports."
    )
    @discord.app_commands.describe(since="Date in YYYY-MM-DD format")
    async def general_report(self, interaction: discord.Interaction, since: str):
        """Slash command handler to trigger insights report."""
        await interaction.response.defer(ephemeral=True)
        until = since

        # Clean up existing rows on both sheets
        meta_clean, ringba_clean = await asyncio.gather(
            self.run_apps_script(META_SHEET_NAME, since),
            self.run_apps_script(RINGBA_SHEET_NAME, since)
        )
        if not (meta_clean and ringba_clean):
            await interaction.followup.send("Cleanup script failed.", ephemeral=True)
            return

        # Fetch Meta insights
        # Pair each BM list with its corresponding token from the .env
        groups = [
            (BM1, ACCESS_TOKENS[0]),
            (BM3, ACCESS_TOKENS[2]),
            (BM4, ACCESS_TOKENS[3]),
        ]

        tasks = []
        for accounts, token in groups:
            for acct in accounts:
                tasks.append(self.fetch_insights(since, until, token, [acct]))
        all_meta = []
        for sub in await asyncio.gather(*tasks):
            all_meta.extend(sub)

        # Save and update Meta
        csv_meta = self.save_insights_to_csv_meta(all_meta, since)
        await self.update_google_sheets(csv_meta)
        await interaction.followup.send(f"Meta insights saved to {csv_meta}.", ephemeral=True)

        # Run Ringba flow
        await self.ringba_insights(interaction, since, defer_response=False)

        # Notify admins
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for uid in ['274730726174490624', '836235560107769867']:
            await self.send_private_message(
                uid,
                f"{timestamp} - {interaction.user.name} ran report for {since}. "
                f"Meta rows: {len(self.new_values_meta)}, Ringba rows: {len(self.new_values_ringba)}"
            )

async def setup(client: commands.Bot):
    """Add this cog to the bot."""
    await client.add_cog(DailyGeneralReport(client))
