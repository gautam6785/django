/*import React from 'react';

let SignupView = React.createClass({
    render() {
   
     some vars for {} 
       do some react soon 
        // let request = require('./node_modules/request');
        // use this lib, example:
         request('http://localhost/publisher/315985618/', function (error, response, body) {
          if (!error && response.statusCode == 200) {
            // window.console.log(response.body); // Show the HTML for the Google homepage.
          } else {
            window.console.log("error");
          }
        });
    


       
    return (
        <div className="signup-container">
        </div>
        
    );
  },

  // end and start a new turn when button is clicked
  openSignupPopover() {
    ga('send', 'event', 'Open Signup Form');
    if ($('video').get(0) != undefined) {
      $('video').get(0).pause();
    }
    mixpanel.track("open signup popover");
    var modalInstance = $modal.open({
      templateUrl: 'signup_popover.html',
      windowClass: 'signup-modal-window',
      backdropClass: 'blackout',
      controller: 'SignupPopoverController',
      size: size
    });

    $.material.init();


    modalInstance.result.then(function () {
    }, function () {
      if ($('video').get(0) != undefined) {
        $('video').get(0).play();
      }
    });
  }

});

module.exports = SignupView;
React.render(<SignupView/>, document.getElementById('react'));
*/

var hasOpened = false;
angular.module('theta')

.controller('SignupController', function ($location, $scope, $modal) {
  // open the product selection modal

  $scope.openSignupPopover = function (size) {
    ga('send', 'event', 'Open Signup Form');
    if ($('video').get(0) != undefined) {
      $('video').get(0).pause();
    }
    mixpanel.track("open signup popover");
    var modalInstance = $modal.open({
      templateUrl: 'signup_popover.html',
      windowClass: 'signup-modal-window',
      backdropClass: 'blackout',
      controller: 'SignupPopoverController',
      size: size
    });

    $.material.init();


    modalInstance.result.then(function () {
    }, function () {
      if ($('video').get(0) != undefined) {
        $('video').get(0).play();
      }
    });
  };

  var search = $location.path('/').search();
  if (search.signup && !hasOpened) {
    hasOpened = true;
    $scope.openSignupPopover();
  }

})

.controller('SignupPopoverController', function ($scope, $modalInstance, $http, $window) {
  $scope.cancel = function () {
    if ($('video').get(0) != undefined) {
      $('video').get(0).play();
    }
    $modalInstance.dismiss('cancel');      
  };


  $scope.signUp = function () {
    var url = "/customers/signup/";
    $http.post(url, {username:$scope.email, 
                     name:$scope.name,
                     password:$scope.password}).
    success(function(data, status, headers, config) {
      if (!data.error) {
        ga('send', 'event', 'Signup');
        mixpanel.track("sign up succeeded");     
        var loc = '/';
        setTimeout(function() {
            $window.location.href = loc;
          }, 500
        );
      } else {
        ga('send', 'event', 'Signup Error', data.error, data.error_type);
        $scope.error = data.error;
        $scope.error_type = data.error_type;
        mixpanel.track("sign up failed");     
      }
    }).
    error(function(data, status, headers, config) {
      mixpanel.track("sign up request failed");     
    });
  };
});
