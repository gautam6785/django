/*global thetaUtil:true */
angular.module('theta')

// controller for dasdhboard and drilldowns
.controller('AccountController', function($location, $scope, $http, $modal) {

  $scope.openAddAccountPopover = function (platform, username, display_name) {
	
	$("#myModal").modal('hide');
	
    mixpanel.track("open add account popover - " + platform);
    ga('send', 'event', 'Open Add Account Form');
		$modal.open({
		 templateUrl: 'add_account_popover.html',
		 controller: 'AddAccountInstanceController',
		 resolve: {
		   'platform': function() { return platform; },
		   'username': function() { return username; },
		   'display_name': function() { return display_name; },
		 }
	   });
  };
  
  $scope.openDeleteAccountConfirmPopover = function (platform, username) {
    mixpanel.track("open delete account popover - " + platform);
    $modal.open({
     templateUrl: 'confirm_delete_account_popover.html',
     controller: 'ConfirmDeleteAccountInstanceController',
     size: 'sm',
     resolve: {
       'platform': function() { return platform; },
       'username': function() { return username; },
     }
   });
  };
  
})


.controller('AddAccountInstanceController', function ($location, $window, $http, $scope, $modal, $modalInstance, platform, username, display_name) {
  $scope.loadingAccount = false;
  $scope.username = username;
  $scope.display_name = display_name;
  if (username) {
    $scope.isUpdate = true;
  }
  $scope.salesPlatform = platform;
  if (platform == "iTunes Connect") {
    $scope.platformIconURL = "/static/img/apple-bite.png"
  } else {
    $scope.platformIconURL = "/static/img/android.png"
  }

  $scope.addAccount = function () {
    $scope.loadingAccount = true;
    var url = "/customers/update_sales_reports_account/";
    //var url = "/dashboard/googlelogin/";
    var req = {
      method: 'POST',
      url: url,
      headers: {
        'Content-Type': null,
        "X-CSRFToken": thetaUtil.getCookie('csrftoken')
      },
      data: { "platform":$scope.salesPlatform,
              "username":$scope.username,
              "password":$scope.password,
              "display_name":$scope.display_name,
      }
    };
    $http(req).then(function(response) {
        if (!response.data.error) {
			
			if(response.data.login == true && response.data.step2_verification == true){
				mixpanel.track("Add Account", {"success":true, "platform":platform});
			    ga('send', 'event', 'Add Account');
			    $scope.loadingAccount = false;
			    $scope.accountSyncMessage = response.data.message;
			    $scope.login_info_id = response.data.login_info_id;
			    
		        $modal.open({
					templateUrl: 'verification.html',
					size : 'lg',
					controller: 'VerficationInstanceController',
					resolve: {
					   'platform': function() { return $scope.salesPlatform; },
					   'username': function() { return $scope.username; },
					   'login_info_id': function() { return $scope.login_info_id; },
					}
				})
		    }
			else if (response.data.message) {
			  mixpanel.track("Update Account", {"success":true, "platform":platform});
			  ga('send', 'event', 'Update Account');
			  $scope.loadingAccount = false;
			  $scope.accountSyncMessage = response.data.message;
			} else {
			  mixpanel.track("Add Account", {"success":true, "platform":platform});
			  ga('send', 'event', 'Add Account');
			  setTimeout(function() {
				$window.location.reload();
			  }, 3000);
			}
		 } else {
			mixpanel.track("Add Account Error", {"success":false, "platform":platform});
			ga('send', 'event', 'Add Account', 'Error', response.data.error);
			$scope.loadingAccount = false;
			$scope.accountSyncError = response.data.error;
		  }
      
    });
  };

  $scope.cancel = function () {
    $modalInstance.dismiss('cancel');
    mixpanel.track("Cancel Add Account");
  };

})


.controller('VerficationInstanceController', function ($location, $window, $http, $scope, $modal, $modalInstance, platform, username) {
	$scope.username = username;

    $scope.showIframe = false;
    $scope.showVerification = true;
    $scope.showVerificationFailed = false;
    $scope.loadingAccount = false;

    $scope.openVerificationAccountPopover = function (platform) {
        var url = "/customers/get_2_step_verification_page/";

        $scope.loadingAccount = true;
        $scope.showVerification = false;
        $scope.showVerificationFailed = false;
        $scope.showIframe = false;
        $scope.salesPlatform = platform;

        var req = {
            method: 'POST',
            url: url,
            headers: {
                'Content-Type': null,
                "X-CSRFToken": thetaUtil.getCookie('csrftoken')
            },
            data: {}
        };

        $http(req).then(function(response) {
            if (!response.data.error) {
                $scope.loadingAccount = false;
                $scope.codeSource = response.data.codeSource;
                $scope.template = response.data.template;

                var googleIframe = window.document.getElementById('verification_google_iframe');
                if(navigator.userAgent.toLowerCase().indexOf('firefox') > -1) {
                    googleIframe.contentWindow.document.designMode = "on";
                }
                else {
                    googleIframe.contentWindow.document.open('text/htmlreplace');
                }
                googleIframe.contentWindow.document.write($scope.template);
                if(navigator.userAgent.toLowerCase().indexOf('firefox') > -1) {
                    googleIframe.contentWindow.document.designMode = "off";
                }
                googleIframe.contentWindow.document.close();
                $scope.showIframe = true;
            }
        });

        var eventMethod = window.addEventListener ? "addEventListener" : "attachEvent";
        var messageEvent = eventMethod == "attachEvent" ? "onmessage" : "message";
        var removeMetod = window.addEventListener ? "removeEventListener" : "detachEvent";
        var eventer = window[eventMethod];
        var removal = window[removeMetod];

        var eventFunction = function(e) {
            var key = e.message ? "message" : "data";
            var data = e[key];

            if (data == "timeoutCondition") {
                $scope.setTimeoutCondition()
            } else {
                var messagePart = data.split(': ');
                if (messagePart[0] == 'code')
                    $scope.verficationAccount(messagePart[1])
            }
        };

        removal(messageEvent, eventFunction, false);
        eventer(messageEvent, eventFunction, false);
    };

    $scope.setTimeoutCondition = function () {
        $scope.showVerificationFailed = true;
        $scope.showIframe = false;
        $scope.$apply()
    };

    $scope.verficationAccount = function (code) {
        var url = "/customers/step2_verification/";
        $scope.loadingAccount = true;
        $scope.showIframe = false;

        var req = {
            method: 'POST',
            url: url,
            headers: {
                'Content-Type': null,
                "X-CSRFToken": thetaUtil.getCookie('csrftoken')
            },
            data: {
                "platform":     $scope.salesPlatform,
                "smscode":      code,
                "codeSource":   $scope.codeSource
            }
        };

        $http(req).then(function(response) {
            if (!response.data.error) {
                mixpanel.track("Add Account", {"success":true, "platform": $scope.salesPlatform});
                ga('send', 'event', 'Add Account');
                $window.location.reload();
            } else if (response.data.error == "Wrong code") {
                mixpanel.track("Add Account Error", {"success":false, "platform": $scope.salesPlatform});
                ga('send', 'event', 'Add Account', 'Error', response.data.error);

                $scope.loadingAccount = false;
                $scope.template = response.data.template;

                var googleIframe = window.document.getElementById('verification_google_iframe');
                googleIframe.contentWindow.document.open('text/htmlreplace');
                googleIframe.contentWindow.document.write($scope.template);
                googleIframe.contentWindow.document.close();
                $scope.showIframe = true;
            } else {
                mixpanel.track("Add Account Error", {"success":false, "platform": $scope.salesPlatform});
                ga('send', 'event', 'Add Account', 'Error', response.data.error);
                $scope.loadingAccount = false;
                $scope.accountSyncError = response.data.error;
            }
        });
    };

	$scope.cancel = function () {
        $modalInstance.dismiss('cancel');
        mixpanel.track("Cancel Verfication");
    };
})


.controller('ConfirmDeleteAccountInstanceController', function ($http, $scope, $modalInstance, platform, username) {
	  $scope.username = username;
	  $scope.salesPlatform = platform;

	  $scope.deleteAccount = function () {
		var url = "/customers/delete_sales_reports_account/";
		var req = {
		  method: 'POST',
		  url: url,
		  headers: {
			'Content-Type': null,
			"X-CSRFToken": thetaUtil.getCookie('csrftoken')
		  },
		  data: { "platform":$scope.salesPlatform,
				  "username":$scope.username,
		  }
		};
		$http(req).then(function(response) {
		  $modalInstance.dismiss('cancel');
		});
	  };

	  $scope.cancel = function () {
		$modalInstance.dismiss('cancel');
	  };

});

