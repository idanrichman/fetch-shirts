class ConnectionBlockedError(Exception):
    '''raise this when amazon blocks our request and shows a captcha'''
    
def check_response(r):
    # assert r.status_code==200, 'bad response'
    if 'To discuss automated access' in r.text: 
        raise ConnectionBlockedError("You've been blocked, try changing the header_option in config.yaml")
    return True if r.ok else False