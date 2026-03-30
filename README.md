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

### Cron job

Run hourly on the server to keep the page current:

```
0 * * * * cd /home/b7jl/electronic-collections-web-app && python3 generate.py /var/www/html/electronic-collections/index.html
```

### Apache

Drop `.htaccess` into `/var/www/html/electronic-collections/`. It sets the `Content-Security-Policy` header to allow embedding only from `cuny-ols.libanswers.com`. Requires `mod_headers` (`a2enmod headers`).

### LibAnswers iframe

Add an HTML widget to the LibAnswers page:

```html
<iframe id="ecollections" src="https://your-server/electronic-collections/" style="width:100%;border:none;"></iframe>
<script src="https://cdn.jsdelivr.net/npm/iframe-resizer@4/js/iframeResizer.min.js"></script>
<script>iFrameResize({}, '#ecollections')</script>
```
