// override RangeSlider to affect more than one graph
Rickshaw.Graph.RangeSlider = function(args) {
  
  function makeUTC(seconds) {
    return new Date(Date.UTC(1970,0,1,0,0, seconds, 0));
  }

	var element = this.element = args.element;
  var self = this;
  this.addDates = function() {
    $('.slider-date').each(function() {
      $(this).remove();
    });
    $('.ui-slider-handle').each(function(index) {
      if (!self.lastUI) {
        return;
      }
      if (index === 0) {
        var d1 = makeUTC(self.lastUI[0]); 
        $(this).append($("<div class='slider-date'>"+d1.toLocaleDateString('en-US')+"</div>"));
      } else {
        var d2 = makeUTC(self.lastUI[1]); 
        $(this).append($("<div class='slider-date'>"+d2.toLocaleDateString('en-US')+"</div>"));
      }
      });
  };

	var graph = this.graph = args.graph;
    if(graph.constructor === Array){
      self.lastUI = [graph[0].dataDomain()[0], graph[0].dataDomain()[1]];
    	$( function() {
    		$(element).slider( {
    			range: true,
    			min: graph[0].dataDomain()[0],
    			max: graph[0].dataDomain()[1],
    			values: [ 
    			graph[0].dataDomain()[0],
    			graph[0].dataDomain()[1]
    			],
    			slide: function( event, ui ) {
            self.lastUI = ui.values;
    				for(var i=0; i < graph.length; i++){
    					graph[i].window.xMin = ui.values[0];
    					graph[i].window.xMax = ui.values[1];
    					graph[i].update();
              // if we're at an extreme, stick there
              if (graph[i].dataDomain()[0] == ui.values[0]) {
              	graph[i].window.xMin = undefined;
              }
              if (graph[i].dataDomain()[1] == ui.values[1]) {
              	graph[i].window.xMax = undefined;
              }
            }
            self.addDates();
          }
      } );  
    	} );
      self.addDates();

    	graph[0].onUpdate( function() {
    		var values = $(element).slider('option', 'values');
    		$(element).slider('option', 'min', graph[0].dataDomain()[0]);
    		$(element).slider('option', 'max', graph[0].dataDomain()[1]);
    		if (graph[0].window.xMin === undefined) {
    			values[0] = graph[0].dataDomain()[0];
    		}
    		if (graph[0].window.xMax === undefined) {
    			values[1] = graph[0].dataDomain()[1];
    		}
    		$(element).slider('option', 'values', values);
    	} );
    } else {
    	$( function() {
    		$(element).slider( {
    			range: true,
    			min: graph.dataDomain()[0],
    			max: graph.dataDomain()[1],
    			values: [ 
    			graph.dataDomain()[0],
    			graph.dataDomain()[1]
    			],
    			slide: function( event, ui ) {
                //original slide function
                graph.window.xMin = ui.values[0];
                graph.window.xMax = ui.values[1];
                graph.update();

                // if we're at an extreme, stick there
                if (graph.dataDomain()[0] == ui.values[0]) {
                	graph.window.xMin = undefined;
                }
                if (graph.dataDomain()[1] == ui.values[1]) {
                	graph.window.xMax = undefined;
                }
              }
            } );
    	} );

    	graph.onUpdate( function() {
    		var values = $(element).slider('option', 'values');
    		$(element).slider('option', 'min', graph.dataDomain()[0]);
    		$(element).slider('option', 'max', graph.dataDomain()[1]);
    		if (graph.window.xMin === undefined) {
    			values[0] = graph.dataDomain()[0];
    		}
    		if (graph.window.xMax === undefined) {
    			values[1] = graph.dataDomain()[1];
    		}
    		$(element).slider('option', 'values', values);
    	} );
    }
  };


Rickshaw.Graph.Legend = Rickshaw.Class.create( {

  className: 'rickshaw_legend',

  initialize: function(args) {
    var graph = this.graph = args.graph;
    this.element = args.element;
    if(graph.constructor === Array){
      this.graphs = graph;
      this.graph = graph[0];
    } else {
      this.graph = graph;
    }

    this.naturalOrder = args.naturalOrder;
    if (!this.element) {
      return; 
    }
    this.element.classList.add(this.className);

    this.list = document.createElement('ul');
    this.element.appendChild(this.list);

    this.render();

    // we could bind this.render.bind(this) here
    // but triggering the re-render would lose the added
    // behavior of the series toggle
    if (this.graphs) {
      for (var i=0;i<this.graphs.length;i++) {
        this.graphs[i].onUpdate( function() {} );
      }
    } else {
      this.graph.onUpdate( function() {} );
    }
  },

  render: function() {
    var self = this;

    while ( this.list.firstChild ) {
      this.list.removeChild( this.list.firstChild );
    }
    this.lines = [];

    var series;
    if (this.graphs) {
      series = [[], []];
      for (var i=0;i<this.graphs.length;i++) {
        series[0].push(this.graphs[i].series[0]);
        series[1].push(this.graphs[i].series[1]);
        if (!this.naturalOrder) {
          series[0] = series[0].reverse();
          series[1] = series[1].reverse();
        }
      }
    } else {
      series = this.graph.series
        .map( function(s) { return s; } );
      if (!this.naturalOrder) {
        series = series.reverse();
      }
    }
  
     series.forEach( function(s) {
      self.addLine(s);
    } );


  },

  addLine: function (series) {
   if(series.constructor === Array){
      this.multiSeries = series;
      series = series[0];
    }
    var line = document.createElement('li');
    line.className = 'line';
    if (series.disabled) {
      line.className += ' disabled';
    }
    if (series.className) {
      d3.select(line).classed(series.className, true);
    }
    var swatch = document.createElement('div');

    if (false && this.multiSeries && this.lines.length === 0) {
      var topTriangle = document.createElement('div');
      topTriangle.className = 'triangle-topleft';
      var bottomTriangle = document.createElement('div');
      bottomTriangle.className = 'triangle-bottomright';
      swatch.appendChild(topTriangle);
      swatch.appendChild(bottomTriangle);
    } else {
      swatch.style.backgroundColor = series.color;
    }

    swatch.className = 'swatch';
    line.appendChild(swatch);

    var label = document.createElement('span');
    label.className = 'label';
    if (this.multiSeries && this.lines.length === 0) {
      label.innerHTML = "Current Period";      
    } else if (this.multiSeries && this.lines.length == 1) {
      label.innerHTML = "Previous Period";      
    } else {
      label.innerHTML = series.name;      
    }

    line.appendChild(label);
    this.list.appendChild(line);

    line.series = series;

    if (series.noLegend) {
      line.style.display = 'none';
    }

    var _line = { element: line, series: series };   
    if (this.multiSeries) {
      _line = { element: line, series: this.multiSeries };   
    }   
    if (this.shelving) {
      this.shelving.addAnchor(_line);
      this.shelving.updateBehaviour();
    }
    if (this.highlighter) {
      this.highlighter.addHighlightEvents(_line);
    }
    this.lines.push(_line);
    return line;
  }
} );

// hack the legend toggle to make it multigraph
  Rickshaw.Graph.Behavior.Series.Toggle = function(args) {

  var graph = this.graph = args.graph;
  if(this.graph.constructor === Array){
    this.graphs = graph;
    graph = graph[0];
  }

  this.legend = args.legend;
  var self = this;

  this.addAnchor = function(line) {

    var anchor = document.createElement('a');
    anchor.innerHTML = '&#10004;';
    anchor.classList.add('action');
    anchor.style.position = "absolute";
    anchor.style.left = "6px";
    anchor.style.color = "white";
    line.element.style.display = "block";
    line.element.insertBefore(anchor, line.element.firstChild);

    anchor.onclick = function() {
      var series = line.series;
      if (line.series.constructor == Array) {
        series = line.series[0];
        if (series.disabled) {
          for (var i=0;i<line.series.length;i++) {
            line.series[i].enable();
          }
          line.element.classList.remove('disabled');
        } else {
          for (var k=0;k<line.series.length;k++) {
            line.series[k].disable();
          }
          line.element.classList.add('disabled');
        }
      }
      if (self.graph.constructor === Array) {
        for (var j=0;j<self.graph.length;j++) {
          self.graph[j].update();
        }
      } else {        
        self.graph.update();
      }

    }.bind(this);
    
    var label = line.element.getElementsByTagName('span')[0];
    label.onclick = anchor.onclick;

  };

  if (this.legend) {

    var $ = jQuery;
    if (typeof $ != 'undefined' && $(this.legend.list).sortable) {

      $(this.legend.list).sortable( {
        start: function(event, ui) {
          ui.item.bind('no.onclick',
            function(event) {
              event.preventDefault();
            }
          );
        },
        stop: function(event, ui) {
          setTimeout(function(){
            ui.item.unbind('no.onclick');
          }, 250);
        }
      });
    }
    if (!this.legend.lines) {
      return;
    }
    this.legend.lines.forEach( function(l) {
      self.addAnchor(l);
    } );
  }

  this.addFunctionToLines = function(graph) {
    graph.series.forEach( function(s) {      
      s.disable = function() {
        if (graph.series.length <= 1) {
          throw('only one series left');
        }
        s.disabled = true;
      };
      s.enable = function() {
        s.disabled = false;
      };
    });
  };

  this._addBehavior = function() {

    if (this.graphs) {
      var self = this;
      this.graphs.forEach( function(graph) { 
        self.addFunctionToLines(graph);
      });
      return;
    }
    this.addFunctionToLines(this.graph);

  };

  this._addBehavior();

  this.updateBehaviour = function () { this._addBehavior(); };

};
