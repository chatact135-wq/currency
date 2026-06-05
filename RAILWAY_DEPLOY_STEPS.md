# Railway Deploy Steps

1. Upload this ZIP to GitHub or Railway.
2. Railway should detect Python automatically.
3. Start command is already set in `railway.json`:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180
```

4. If Railway still fails, open Deploy Logs and check:
   - Did `pip install -r requirements.txt` complete?
   - Is `gunicorn` installed?
   - Is the app listening on `$PORT`?

## Common fixed issue

The previous package had a Procfile using gunicorn but requirements.txt did not include gunicorn.  
This version fixes that.
