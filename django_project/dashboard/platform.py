#######################################
platforms = {
	'0001': {
		'itunes': {
					'fields' : [
					{'disp':'Display Name',
					 'name':'display_name',
					 'type':'text',
					},
					{'disp':'User Id',
					 'name':'user_id',
					 'type':'text',
					},
					{'disp':'User Signature',
					 'name':'user_sig',
					 'type':'password',
					},
					],
					'submit': ['', 'Add Account'],
					'message': 'chratboost message',
					'label': 'iTunes Connect',
					'icon': 'app-store.jpeg',
			},
		'googleplay': {
					'fields' : [
					{'disp':'Display Name',
					 'name':'display_name',
					 'type':'text',
					},
					{'disp':'User Id',
					 'name':'user_id',
					 'type':'text',
					},
					{'disp':'User Signature',
					 'name':'user_sig',
					 'type':'password',
					},
					],
					'submit': ['', 'Add Account'],
					'message': 'chratboost message',
					'label': 'Google Cloud',
					'icon': 'google-play.png',
			},
		
	},
	'0002': {
		'admob': {
			'fields' : [],
			'submit': ['','Connect with Google'],
			'message': 'admob message',
			'label': 'AdMob',
			'icon': 'ad-mob.png',
		},
		'chartboost': {
					'fields' : [
					{'disp':'Display Name',
					 'name':'display_name',
					 'type':'text',
					},
					{'disp':'User Id',
					 'name':'user_id',
					 'type':'text',
					},
					{'disp':'User Signature',
					 'name':'user_sig',
					 'type':'password',
					},
					],
					'submit': ['', 'Add Account'],
					'message': 'chratboost message',
					'label': 'Chartboost',
					'icon': 'chartboost.png',
			},
		'facebook': {
					'fields' : [],
					'submit' : ['', 'Connect with Facebook'],
					'message': 'facebook message',
					'label': 'Facebook',
					'icon': 'facebook.png',
			},
	}
} 
