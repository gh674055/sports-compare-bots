from requests_ip_rotator import ApiGateway

gateway = ApiGateway("https://www.baseball-reference.com", verbose=True)
gateway.start()
gateway.shutdown()

gateway = ApiGateway("https://www.pro-football-reference.com", verbose=True)
gateway.start()
gateway.shutdown()

gateway = ApiGateway("https://www.hockey-reference.com", verbose=True)
gateway.start()
gateway.shutdown()