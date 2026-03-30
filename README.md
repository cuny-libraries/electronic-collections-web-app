# electronic-collections-web-app
For the Alma Extensibility Task Force

`generate.py` queries the Alma API to retrieve the activated Network Zone electronic collections at CUNY and writes a self-contained `index.html`. The page is served statically on Apache and embedded as an iframe in the OLS LibAnswers Knowledge Base.

## Setup

1. Copy `.env.sample` to `.env` and fill in your API keys:
   ```
   NZ_API_KEY=...
   BIBS_NZ_API_KEY=...
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

```
python3 generate.py [output_path]
```

`output_path` defaults to `./index.html`. On the server, pass the full path:

```
python3 generate.py /var/www/html/electronic-collections/index.html
```

## Deployment

### Server setup

The repo should live in your home directory, keeping credentials out of the web root. The generated `index.html` is written directly to the Apache-served directory.

SSH into the server and run:

```
git clone -b static-site https://github.com/cuny-libraries/electronic-collections-web-app.git ~/electronic-collections-web-app
cd ~/electronic-collections-web-app
pip install -r requirements.txt
```

Create the `.env` file with your API keys:

```
cp .env.sample .env
nano .env
```

Make sure the output directory exists:

```
mkdir -p /var/www/html/electronic-collections
```

Run the script once to verify everything works:

```
python3 generate.py /var/www/html/electronic-collections/index.html
```

### Cron job

A cron job runs `generate.py` automatically on a schedule to keep the page current. Cron jobs are stored in a per-user file called a crontab.

To open (or create) your crontab for editing, run:

```
crontab -e
```

This opens the file in a text editor (usually `nano`). Add the following line to run the script every hour:

```
0 * * * * cd ~/electronic-collections-web-app && python3 generate.py /var/www/html/electronic-collections/index.html
```

The format is: `minute hour day month weekday command`. `0 * * * *` means "at minute 0 of every hour".

Save and exit (`Ctrl+O`, then `Enter`, then `Ctrl+X` in nano). To verify the cron job was saved, run:

```
crontab -l
```

### LibAnswers iframe

Add an HTML widget to the LibAnswers page:

```html
<iframe id="ecollections" src="https://your-server/electronic-collections/" style="width:100%;border:none;"></iframe>
<script src="https://cdn.jsdelivr.net/npm/iframe-resizer@4/js/iframeResizer.min.js"></script>
<script>iFrameResize({}, '#ecollections')</script>
```
