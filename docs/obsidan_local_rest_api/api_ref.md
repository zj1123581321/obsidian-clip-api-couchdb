#  Creates a new file in your vault or updates the content of an existing one if the specified file already exists.

## 请求

```
curl -X 'PUT' \
  'http://127.0.0.1:27123/vault/test.md' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer xxx' \
  -H 'Content-Type: text/markdown' \
  -d '# This is my document

something else here
'
```
其中 url 里的 `test.md` 指的是 Path to the relevant file (relative to your vault root).可以带文件夹路径。


## 响应

```
Code	Details
204	
Responses
Code	Description	Links
204	
Success

No links
400	
Incoming file could not be processed. Make sure you have specified a reasonable file name, and make sure you have set a reasonable 'Content-Type' header; if you are uploading a note, 'text/markdown' is likely the right choice.

Media type

application/json
Example Value
Schema
{
  "errorCode": 40149,
  "message": "A brief description of the error."
}
No links
405	
Your path references a directory instead of a file; this request method is valid only for updating files.

Media type

application/json
Example Value
Schema
{
  "errorCode": 40149,
  "message": "A brief description of the error."
}
```

# Returns basic details about the server
Returns basic details about the server as well as your authentication status.

This is the only API request that does not require authentication.

## 请求

```
curl -X 'GET' \
  'http://127.0.0.1:27123/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer xxx'
```

## 示例响应

```
{
  "status": "OK",
  "manifest": {
    "id": "obsidian-local-rest-api",
    "name": "Local REST API",
    "version": "3.2.0",
    "minAppVersion": "0.12.0",
    "description": "Get, change or otherwise interact with your notes in Obsidian via a REST API.",
    "author": "Adam Coddington",
    "authorUrl": "https://coddingtonbear.net/",
    "isDesktopOnly": true,
    "dir": ".obsidian/plugins/obsidian-local-rest-api"
  },
  "versions": {
    "obsidian": "1.9.10",
    "self": "3.2.0"
  },
  "service": "Obsidian Local REST API",
  "authenticated": true,
  "certificateInfo": {
    "validityDays": 364.97681943287034,
    "regenerateRecommended": false
  },
  "apiExtensions": []
}
```