function ThetaUtil () {}


var thetaUtil = new ThetaUtil();

ThetaUtil.prototype.kFormatter = function(num) {
	return num > 999 ? (num/1000).toFixed(1) + 'k' : num;
};


ThetaUtil.prototype.MAIN_COLOR = '#340B59';


ThetaUtil.prototype.ALL_SUBCATEGORY = {"name":"All", 
                                            "id":-999};


ThetaUtil.prototype.secondsInADay = function() {
	return 24*60*60;
};


// chunk an array into rows of a given size, for bootstrap display
ThetaUtil.prototype.chunk = function(arr, size) {
  var rows = [];
  for (var i=0; i<arr.length; i+=size) {
    rows.push(arr.slice(i, i+size));
  }
  return rows;
};


// using jQuery
ThetaUtil.prototype.getCookie = function(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
	};


// style rickshaw hover overlay for realtime graph
ThetaUtil.prototype.hoverFormatterForName = function(name) {
	var self = this;
	// \todod ask dan or anna why this works
	var func = 
		function(_, x, y) {
	    return self.hoverFormatForName(x, y, name);
		};
	return func;
};


// style rickshaw hover overlay for realtime graph
ThetaUtil.prototype.hoverFormatForName = function(x, y, name) {
  var date = '<span class="date">' + this.localTimeStringForDate(new Date(x * 1000), true) + '</span>';
  var swatch = '<span class="detail_swatch" style="background-color:#0b589c"></span>';
  var content = swatch + " " + parseInt(y) + ' ' + name + '<br>' + date;
  return content;
 };


// style rickshaw hover overlay for realtime graph
ThetaUtil.prototype.dateHoverFormatterForName = function(name) {
  var self = this;
  // \todod ask dan or anna why this works
  var func = 
    function(_, x, y) {
      return self.dateHoverFormatForName(x, y, name);
    };
  return func;
};


// style rickshaw hover overlay for realtime graph
ThetaUtil.prototype.dateHoverFormatForName = function(x, y, name) {
  var date = '<span class="date">' + (new Date(x * 1000)).toLocaleDateString() + '</span>';
  var swatch = '<span class="detail_swatch" style="background-color:#0b589c"></span>';
  var content = swatch + " " + parseInt(y) + ' ' + name + '<br>' + date;
  return content;
 };


ThetaUtil.prototype.reverseFormat = function(value) {
  return -value;
}

ThetaUtil.prototype.getTimeUnit = function(seconds) {
  var unit = {};
  var self = this;
  unit.formatTime = function(d) {
    return moment(d).format('h:mm a');
  };
  unit.formatter = function(d) { return this.formatTime(d);};
  unit.seconds = seconds;
  return unit;
};

ThetaUtil.prototype.getDateUnit = function(seconds) {
  var unit = {};
  var self = this;
  unit.formatTime = function(d) {
    return moment(d).format('MMM D');
  };
  unit.seconds = seconds;
  unit.formatter = function(d) { return this.formatTime(d);};
  return unit;
};



ThetaUtil.prototype.localTimeStringForDate = function(date, isLong){
	var now = date, 
	ampm = 'am', 
	h = now.getHours(), 
	m = now.getMinutes(), 
	s = now.getSeconds();
	if (h >= 12){
	  ampm = 'pm';
	  if(h>12) {
	    h -= 12;
	  }
	}

	if (h === 0) {
	  h += 12;
	}
	if (m < 10) {
	  m = '0' + m;
	}
	if (s < 10) {
	  s = '0' + s;
	}

	if (isLong) {
	  return h + ':' + m  + ' ' + ampm;
	}
	return h + ':' + m;
};


ThetaUtil.prototype.defaultGraphOptions = function() {
	return { 
          "stroke":true, 
          "min":'auto', 
          "dotSize": 3,
          "renderer": 'multi',
          "preserve":true,
          "width":250, 
          "height":120, 
          "padding": {"top": 0.07, "left": 0.02, "right": 0.02, "bottom":0.07}
         };
};


ThetaUtil.prototype.sigFigs = function(n, sig) {
  var mult = Math.pow(10, sig - Math.floor(Math.log(n) / Math.LN10) - 1);
  return Math.round(n * mult) / mult;
}


// polyfill startsWith for ecma 5
if (!String.prototype.startsWith) {
  Object.defineProperty(String.prototype, 'startsWith', {
    enumerable: false,
    configurable: false,
    writable: false,
    value: function(searchString, position) {
      position = position || 0;
      return this.lastIndexOf(searchString, position) === position;
    }
  });
}


// Production steps of ECMA-262, Edition 5, 15.4.4.21
// Reference: http://es5.github.io/#x15.4.4.21
if (!Array.prototype.reduce) {
  Array.prototype.reduce = function(callback /*, initialValue*/) {
    'use strict';
    if (this == null) {
      throw new TypeError('Array.prototype.reduce called on null or undefined');
    }
    if (typeof callback !== 'function') {
      throw new TypeError(callback + ' is not a function');
    }
    var t = Object(this), len = t.length >>> 0, k = 0, value;
    if (arguments.length == 2) {
      value = arguments[1];
    } else {
      while (k < len && ! k in t) {
        k++; 
      }
      if (k >= len) {
        throw new TypeError('Reduce of empty array with no initial value');
      }
      value = t[k++];
    }
    for (; k < len; k++) {
      if (k in t) {
        value = callback(value, t[k], k, t);
      }
    }
    return value;
  };
}


var indexOf = function(needle) {
    if(typeof Array.prototype.indexOf === 'function') {
        indexOf = Array.prototype.indexOf;
    } else {
        indexOf = function(needle) {
            var i = -1, index = -1;

            for(i = 0; i < this.length; i++) {
                if(this[i] === needle) {
                    index = i;
                    break;
                }
            }

            return index;
        };
    }

    return indexOf.call(this, needle);
};