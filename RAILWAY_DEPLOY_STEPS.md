# Railway Deploy — EdgeFlow Terminal Pro Live Test V1

1. Deploy this ZIP / repo to Railway.
2. Add environment variable:

```text
TWELVEDATA_API_KEY=your_key
```

3. Make sure Railway Custom Start Command is empty.
4. Open:

```text
/
```

or:

```text
/dashboard
```

5. Test:

```text
/health
/api/signals
/debug
```

Important:
If API key is missing, the dashboard uses DEMO FALLBACK data and is NOT for trading.
