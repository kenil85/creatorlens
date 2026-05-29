from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
print('URL:', url)
print('KEY:', key[:30] if key else 'MISSING')

try:
    client = create_client(url, key)
    result = client.table('video_chunks').select('id').limit(1).execute()
    print('SUCCESS:', result)
except Exception as e:
    print('ERROR:', str(e))