class ConnectionBlockedError(Exception):
    '''raise this when amazon blocks our request and shows a captcha'''
    
class PageNotFoundError(Exception):
    '''raise this when amazon product page no longer available'''
    
def check_response(r):
    # assert r.status_code==200, 'bad response'
    # if blocked then the "to discuss automated access" string appears in the page, but for some reason it also in the text
    # when the page is not found (error 404)
    if (r.status_code == 404):
        raise PageNotFoundError("Error 404: page %s not found" % r.url)
    elif 'To discuss automated access' in r.text:
        raise ConnectionBlockedError("You've been blocked, try changing the header_option in config.yaml")
    return True if r.ok else False