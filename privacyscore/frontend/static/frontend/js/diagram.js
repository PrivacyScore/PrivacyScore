function getData(site_id) {
	
	//var list_id = global_list_id;
	var scan_group_id = [];
	
	var groupsLength = document.getElementById("diagram-box-settings-scandate").getElementsByClassName("checkbox").length;

	
	
	var labels = [];
	var sites = [];
	var groups = [];
	var datasets = [];
	
	for (var i=0; i<groupsLength; i++) {
		var id = "group-" + i;
		if (document.getElementById(id).checked) {
			groups.push(document.getElementById(id).value);
		}
	}
	// for (var i=0; i<sitesLength; i++) {
		// var id = "site-" + i;
		// if (document.getElementById(id).checked) {
			// sites.push(document.getElementById(id).value);
		// }
	// }
	

	  
	  var datasets
	  
	  	
		$.ajax({
            url: apiUrl + '/Statistics',
            type: 'GET',
			async: false,
			data: {
				"source": "site",
				"sourceid": global_diagram_site,
				"typet": "all",
				"presentation": "time"	//todo: change to time
			},
			xhrFields: {
				withCredentials: true
			},
            success: function (data) {
				data = JSON.parse(data);
				console.log(data);
				datasets = data;
				
            }
        });
		

		
		
		
	$( function() {
		$( "#slider-range" ).slider({
		  range: true,
		  min: 0,
		  max: datasets.starttime.length-1,
		  minRange: 2,
		  values: [0, datasets.starttime.length-1],
		  slide: function( event, ui ) {
			$( "#amount" ).val( "" + getDate(datasets.starttime[ui.values[ 0 ]], langData.timeFormat, langData.dateFormat) + " - " + getDate(datasets.starttime[ui.values[ 1 ]], langData.timeFormat, langData.dateFormat) );
			$( "#indizes" ).val( "" +ui.values[ 0 ] + "-" + ui.values[ 1 ] );
		  }
		});
		$( "#amount" ).val( "" + getDate(datasets.starttime[$( "#slider-range" ).slider( "values", 0 )], langData.timeFormat, langData.dateFormat) +
		  " - " + getDate(datasets.starttime[$( "#slider-range" ).slider( "values", 1 )], langData.timeFormat, langData.dateFormat) );
		  $( "#indizes" ).val( "" + $( "#slider-range" ).slider( "values", 0 ) +
		  "-" + $( "#slider-range" ).slider( "values", 1 ) );
	  } );
	  
	  // get slider values
	  var startIndex = parseInt(document.getElementById("indizes").value.split("-")[0]);
	  var endIndex = parseInt(document.getElementById("indizes").value.split("-")[1]);
	  
	  //console.log(startIndex);
	  //console.log(endIndex);
	  // get start and end index
	  
	  if (Number.isNaN(startIndex)) {
		 startIndex = 0;
	  }
	  if (Number.isNaN(endIndex)) {
		 endIndex = datasets.starttime.length-1;
	  }
		
		if (startIndex == endIndex) {
			if (startIndex == 0) {
				endIndex++;
			} else {
				startIndex--;
			}
		}
		
	

	
	//get the names the first time
	//for (var siteIndex=0; siteIndex<sites.length; siteIndex++) {
		//labels.push("URL");
	//}

	
	
	//console.log(labels);
	
	
	// für jede site ein objekt (label: name der site)
	// x: 1, 2, 3, 4, ....
	// y: daten 
	
	// var keys = "<h3>Legende</h3>";
	// for (var datasetIndex=0; datasetIndex<datasets.length; datasetIndex++) {
		// var dateString = datasets[datasetIndex].seiten[0].scans[0].starttime;
		// var date = getDate(dateString);
		// keys += "<div>";
		// var index = datasetIndex + 1;
		// keys += index;
		// keys += ": ";
		// keys += date;
		// keys += "</div>";
	// }
	// document.getElementById("diagram_keys").innerHTML = keys;
	
	var selectedData = "";
	var selectedLabel = "";
	
	if (document.getElementById("thirdDiagram").checked) {
		selectedData = "third_party_anzahl";
		selectedLabel = "thirdLabel";
	} else if (document.getElementById("cookiesDiagram").checked) {
		selectedData = "cookies_anzahl";
		selectedLabel = "cookiesLabel";
	} else if (document.getElementById("httpsDiagram").checked) {
		selectedData = "https";
		selectedLabel = "httpsLabel";
	} else if (document.getElementById("thirdReqDiagram").checked) {
		selectedData = "third_party_request_anzahl";
		selectedLabel = "thirdReqLabel";
	}
	
	var data = [];
	
	//for (var siteIndex=0; siteIndex<datasets[0].seiten.length; siteIndex++) {
		//if (sites.toString().indexOf(datasets[0].seiten[siteIndex]._id.$oid)>-1) {
		//if (site_id.indexOf(datasets[0].seiten[siteIndex]._id.$oid)>-1) {
			var x = [];
			var y = [];
			
			for (var datasetIndex=startIndex; datasetIndex<=endIndex; datasetIndex++) {
				x.push(datasetIndex+1);
				// check for criterion
				var currentData;
				// if (document.getElementById("cookies").checked) {
					// currentData = datasets[datasetIndex].seiten[siteIndex].scans[0].flashcookies.length;
					// currentData += datasets[datasetIndex].seiten[siteIndex].scans[0].profilecookies.length;
				// } else if (document.getElementById("score").checked) {
					
				// } else if (document.getElementById("https").checked) {
					// if (datasets[datasetIndex].seiten[siteIndex].scans[0].https) {
						// currentData = 1;
					// } else {
						// currentData = 0;
					// }
				// }
				
				currentData = eval("datasets." + selectedData + "[" + datasetIndex + "]");
				console.log(currentData);
				y.push(currentData);
			}
			var name = eval("langData.scannedList.divs." + selectedLabel);
			
			var helpObject = {label: name, x: x, y: y}
			data.push(helpObject);
		//}
	//}
	return data;
}

function loadDiagram(site_id) {
	

	

	
	

	
	//data = JSON.parse('[{"label":"http://www.n-tv.de/","x":[0,1,2],"y":[52,49,52]},{"label":"http://www.tagesschau.de/","x":[0,1,2],"y":[17,17,17]},{"label":"https://www.nytimes.com/","x":[0,1,2],"y":[51,61,54]}]');

	document.getElementById("loader").style.display = "block";
	createDiagram(getData(site_id));
	//createDiagram(data);
	document.getElementById("loadingProgress").innerHTML = "";
	document.getElementById("loader").style.display = "none";
}


function createDiagram(data) {
	
	console.log(data);

var xy_chart = d3_xy_chart()
    .width(640)
    .height(250)
    .xlabel("")
    .ylabel("") ;
var svg = d3.select("#diagram").append("svg")
    .datum(data)
    .call(xy_chart) ;

function d3_xy_chart() {
    var width = 800,  
        height = 480, 
        xlabel = "",
        ylabel = "" ;
    
    function chart(selection) {
        selection.each(function(datasets) {
            //
            // Create the plot. 
            //
            var margin = {top: 20, right: 180, bottom: 30, left: 50}, 
                innerwidth = width - margin.left - margin.right,
                innerheight = height - margin.top - margin.bottom ;
            
            var x_scale = d3.scaleLinear()
                .range([0, innerwidth])
                .domain([ d3.min(datasets, function(d) { return d3.min(d.x); }), 
                          d3.max(datasets, function(d) { return d3.max(d.x); }) ]) ;
            
            var y_scale = d3.scaleLinear()
                .range([innerheight, 0])
                .domain([ 0,
                          Math.floor(d3.max(datasets, function(d) { return d3.max(d.y); }) * 1.2)]) ;

            var color_scale = d3.scaleOrdinal(d3.schemeCategory10)
                .domain(d3.range(datasets.length)) ;

            var x_axis = d3.axisBottom()
                .tickFormat(d3.format("d"))
				.scale(x_scale)
				.tickValues(data[0].x)
				.ticks(Math.min(10, data[0].x.length-1));

            var y_axis = d3.axisLeft()
				//.tickFormat(d3.format("d"))
                .scale(y_scale)
				//.tickValues(data[0].y)
				.ticks(Math.min(10, Math.floor(d3.max(datasets, function(d) { return d3.max(d.y); }) * 1.2)));

            var x_grid = d3.axisBottom()
                .scale(x_scale)
                .tickSize(-innerheight)
                .tickFormat("")
				.ticks(Math.min(10, data[0].x.length-1));

            var y_grid = d3.axisLeft()
                .scale(y_scale)
                .tickSize(-innerwidth)
                .tickFormat("")
				.ticks(Math.min(10, Math.floor(d3.max(datasets, function(d) { return d3.max(d.y); }) * 1.2)));

            var draw_line = d3.line()
                //.interpolate("basis")
                .x(function(d) { return x_scale(d[0]); })
                .y(function(d) { return y_scale(d[1]); }) ;

            var svg = d3.select(this)
                .attr("width", width)
                .attr("height", height)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")") ;
            
            svg.append("g")
                .attr("class", "x grid")
                .attr("transform", "translate(0," + innerheight + ")")
                .call(x_grid) ;

            svg.append("g")
                .attr("class", "y grid")
                .call(y_grid) ;

            svg.append("g")
                .attr("class", "x axis")
                .attr("transform", "translate(0," + innerheight + ")") 
                .call(x_axis)
                .append("text")
                .attr("dy", "-.71em")
                .attr("x", innerwidth)
                .style("text-anchor", "end")
                .text(xlabel) ;
            
            svg.append("g")
                .attr("class", "y axis")
                .call(y_axis)
                .append("text")
                .attr("transform", "rotate(-90)")
                .attr("y", 6)
                .attr("dy", "0.71em")
                .style("text-anchor", "end")
                .text(ylabel) ;

            var data_lines = svg.selectAll(".d3_xy_chart_line")
                .data(datasets.map(function(d) {return d3.zip(d.x, d.y);}))
                .enter().append("g")
                .attr("class", "d3_xy_chart_line") ;
            
            data_lines.append("path")
                .attr("class", "line")
                .attr("d", function(d) {return draw_line(d); })
                .attr("stroke", function(_, i) {return color_scale(i);}) ;
            
            data_lines.append("text")
                .datum(function(d, i) { return {name: datasets[i].label, final: d[d.length-1]}; }) 
                .attr("transform", function(d) { 
                    return ( "translate(" + x_scale(d.final[0]) + "," + 
                             y_scale(d.final[1]) + ")" ) ; })
                .attr("x", 3)
                .attr("dy", ".35em")
                .attr("fill", function(_, i) { return color_scale(i); })
                .text(function(d) { return d.name; }) ;

        }) ;
    }

    chart.width = function(value) {
        if (!arguments.length) return width;
        width = value;
        return chart;
    };

    chart.height = function(value) {
        if (!arguments.length) return height;
        height = value;
        return chart;
    };

    chart.xlabel = function(value) {
        if(!arguments.length) return xlabel ;
        xlabel = value ;
        return chart ;
    } ;

    chart.ylabel = function(value) {
        if(!arguments.length) return ylabel ;
        ylabel = value ;
        return chart ;
    } ;

    return chart;
}
}