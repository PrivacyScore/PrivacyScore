var resultColumns = ["Bewertung", "HTTPS", "HTTPS-Umleitung", "Anzahl Cookies", "Third Parties", "Third Party Requests", "Alle Webserver in Deutschland", "HSTS-Flags"];
var global_list_id = "";
var global_group = "";
var global_diagram_site = "";
var listData;
var langData;

function loadData() {
	var listid = getUrlVars()["list"];
	var group = getUrlVars()["group"];
	var lang = getUrlVars()["lang"];
	if (lang == null || lang.length<1) {
		lang = "de";
	}
	$.getJSON("/static/frontend/lang/" + lang + ".json", function (data_lang) {
		langData = data_lang;
		resultColumns = langData.scannedList.resultColumns;
		if (group == null) {
			// if no group, get all groups from this list
			$.get(apiUrl + "GetScanGroupsByList/" + listid, function (jsonString) {
			console.log(jsonString);
			
			data = JSON.parse(jsonString);
			console.log(data);
			if (data.length>0 && data[data.length-1].hasOwnProperty("_id") && data[data.length-1].state == "scanning") {
				// get scan group id
				group = data[data.length-1]._id.$oid;
				window.location.href = "scannedList.html?list=" + listid + "&group=" + group;
			} else {
				//refresh after 5 seconds
				if (data.length>0 && data[data.length-1].hasOwnProperty("progress") && data[data.length-1].hasOwnProperty("progress_timestamp")) {
					var html = "<br>..." + data[data.length-1].progress;
					html += "<br>" + data[data.length-1].progress_timestamp;
					document.getElementById("loadingProgress").innerHTML = html;
					//document.getElementById("compareDiv").style.display = "none";
				}
				setTimeout(function(){loadData()}, 5000);
			}
			});
		}
			
		var showall = getUrlVars()["showall"];
		if (showall == "true") {
			showall = true;
		} else {
			showall = false;
		}
		var demo = getUrlVars()["demo"];
		global_group = group;
		var param = "";
		param = listid;
		if (listid != null && demo == null) {
			if (group != null) {
				param += "/" + group;
			}
			var loader = document.getElementById("loader");
			//loader.style.display = "block";
			$.get(apiUrl + "ShowScannedList/" + param, function (jsonString) {
				//jsonString = jsonString.replace(/'/g, '"');
				data = JSON.parse(jsonString);
				//data = JSON.parse(data);
				console.log(data);
				if (data == null || false) {	// todo: 
					document.getElementsByTagName("content").item(0).innerHTML =  "<br>" + langData.scannedList.alerts.noListFoundID.replace("#ID", listid);
				} else if (data.hasOwnProperty("type") && data.type == "error" && data.message == "This list is private. Please login.") {
					document.getElementsByTagName("content").item(0).innerHTML =  "<br>" + langData.scannedList.alerts.noListPrivate;
					document.getElementsByTagName("content").item(0).style.display = "block";
					document.getElementById("loader").style.display = "none";
				} else {
					callback(data, showall);
					console.log(data);
					if (data.seiten[data.seiten.length-1].scans.length<1) {
						setTimeout(function(){loadData()}, 5000);
					}
				}
			});
		} else	{
			alert(langData.scannedList.alerts.noList);
			window.location.href = "browse.html";
		}
});
	
}

function callback(json, showall){
	listData = json;
	//document.getElementById("dashboard").style.display = "block";
	if (json == null) {
		document.getElementsByTagName("content").item(0).innerHTML =  "<br>" + langData.scannedList.alerts.noListFound;
	} else {
		document.getElementsByTagName("content").item(0).style.display = "block";
		
		if (json.seiten[0].scans.length<1) {
			setOldNewScans(json, json._id.$oid, "");
		} else {
		console.log(json);
		setOldNewScans(json, json._id.$oid, json.seiten[0].scans[0].scan_group_id.$oid);
		setCompareScans(json._id.$oid, json.seiten[0].scans[0].scan_group_id.$oid);
		global_list_id = json._id.$oid;
		setTitle(json.name, json.seiten[0].scans[0].starttime);
		setHeader1(json.name);
		//setDate(json.seiten[0].scans[0].starttime);
		setDescription(json.description);
		setTags(json.tags.toString());
		setDashboard(json.seiten);
		setThirdPartiesButton(json._id.$oid, json.seiten[0].scans[0].scan_group_id.$oid);
		setNewListButton(json._id.$oid, json.seiten[0].scans[0].scan_group_id.$oid);
		setDeleteButton(json.userid.$oid);
			
		var columns = json.columns.length + resultColumns.length + 1; // +1 for link column
		var rows = json.seiten.length;
		
		margin = columns*38;
		margin = Math.min(155, margin);
		document.getElementsByTagName("content").item(0).style.marginBottom = margin + "px";
		
		drawTable(columns, rows);
		fillTable(createTableHeadContent(json), createTableBody(json), -1);
		
		// set height for table body
		//var height = Math.min($(window).height()-275,rows*39);
		//document.getElementsByTagName("tbody").item(0).style.maxHeight = ""+height+"px";
		
		var visibleArray = [];
		visibleArray.push(true); // true for first column (link)
		for (var i=0; i<json.columns.length; i++) {
			visibleArray.push(json.columns[i].visible);
		}
			
		setTableSettings(rows, json.columns.length+1, visibleArray, showall); // sort by the first column in resultColumns
			
		document.getElementById("compareDiv").style.display = "block";
		document.getElementById("dashboard").style.display = "block";
		document.getElementById("listScanning").style.display = "none";
		document.getElementById("compareCheckbox").checked = false;

		}
		
		
	}
	var loader = document.getElementById("loader");
	loader.style.display = "none";
}

function setTableSettings(rows, sorting, visibleArray, showall) {

	var height = calculateHeight(rows);
	var displayLength = 25;
	var showallText = langData.scannedList.dataTables.buttonExpand;
	
	if (showall) {
		height = false;
		displayLength = -1;
		showallText = langData.scannedList.dataTables.buttonCollapse;
	}
	
	  $(document).ready(function() {
			var datatablesLanguagePath = "" + langData.lang + "_datatables.json";
			var table = $('#list_table').DataTable( {
				"responsive": true,
				//"fixedColumns": true,
				//fixedColumns:   {
					//leftColumns: 1,
					//rightColumns: 0
				//},
				scrollCollapse: false,
				"scrollX": "100%",
				"scrollXInner": "100%",
				"scrollY": height,
				"iDisplayLength": displayLength,
				"order": [[ sorting, "asc" ]],
				"pagingType": "full_numbers",
				
				dom: 'rtBfip',
				language: {
					"url": datatablesLanguagePath,
					buttons: {
						pageLength: langData.scannedList.dataTables.buttonPageLength
					}
				},
				lengthMenu: [
					[5, 10, 25, -1 ],
					['5', '10', '25', 'Alle' ]
						],
				buttons: ['pageLength',
						{ text: showallText, action: function () {expandList(showall);} },
						{ extend: 'colvis', text: langData.scannedList.dataTables.buttonColvis },
						{ extend: 'csv', text: langData.scannedList.dataTables.buttonCsv },
						{ extend: 'pdfHtml5', text: langData.scannedList.dataTables.buttonPdf}
						]
			} );
			
			$('#list_table').css( 'display', 'table' );
			
			// set hidden columns
			for ( var i=0 ; i<visibleArray.length ; i++ ) {
				if (!visibleArray[i]) {
					table.column( i ).visible( false, false );
				}
			}
			
			table.responsive.recalc(); // recalculate column widths

	
			
//  table.columns().iterator( 'column', function (ctx, idx) {
//    $( table.column(idx).header() ).append('<span class="sort-icon"/>');
//  } );
		} );
}

function fillTable(tableHeadContent, tableBody, oldLen) {
	console.log(tableHeadContent);
	console.log(tableBody);
	// fill tableHead
	for (var columnIndex=0; columnIndex<tableHeadContent.length; columnIndex++) {
		var id = 'h-' + columnIndex;
		var html = '';
		html += tableHeadContent[columnIndex];
		document.getElementById(id).innerHTML = html;
	}
	// fill tableBody
	for (var rowIndex=0; rowIndex<tableBody.length; rowIndex++) {
		for (var columnIndex=0; columnIndex<tableBody[rowIndex].length; columnIndex++) {
			var id = '' + rowIndex + '-' + columnIndex;
			var html = '';
			// replace the https values (true/false) with glyphicons
			if (tableBody[rowIndex][columnIndex]=="true" || tableBody[rowIndex][columnIndex]=="false" || typeof(tableBody[rowIndex][columnIndex])=="boolean") {
				html += '<span class="glyphicon glyphicon-##GLYPH"><span style="display:none">##RESULT</span></span>';
				if (tableBody[rowIndex][columnIndex]) {
					html = html.replace('##GLYPH','ok');
					html = html.replace('##RESULT','true');
				} else {
					html = html.replace('##GLYPH','remove');
					html = html.replace('##RESULT','false');
				}
			} else if (columnIndex == 0) {
				// if first column (url)
				var site_id = tableBody[rowIndex][columnIndex].site_id;
				var scan_id = tableBody[rowIndex][columnIndex].scan_id;
				// url for the scanned site
				var url = tableBody[rowIndex][columnIndex].url;
				if (url.indexOf("http://")<0 && url.indexOf("https://")<0) {
					url = "http://" + url;
				}
				html += '<a href="' + url + '"><i class="fa fa-link"></i></a> ';	//TODO
				html += '<i class="fa fa-line-chart" onclick="openAndLoadDiagram(\''  + site_id + '\');"></i> ';	//TODO
				// url for the scan.html
				url = './scan.html?lang=' + langData.lang + '&site=' + site_id + '&scan=' + scan_id;
				html += '<a style="color:black;" href="';
				html += url;
				html += '">';
				html += tableBody[rowIndex][columnIndex].url;
				html += '</a>';
			} else {
				html = tableBody[rowIndex][columnIndex];
			}
			document.getElementById(id).innerHTML = html + '<small></small>';;
		}
	}
	if (oldLen>-1) {
		// set page length to oldLen
		var table = $('#list_table').DataTable();
		table.page.len(oldLen).draw();
	}
}

function drawTable(columns, rows) {
	
	var tableHead = '<tr>';
	for (var columnIndex=0; columnIndex<columns; columnIndex++) {
		tableHead += '<th id="h-'
		tableHead += columnIndex;
		tableHead += '" class="all"></th>';
	}
	tableHead += '</tr>';
	
	var tableBody = '';
	for (var rowIndex=0; rowIndex<rows; rowIndex++) {
		tableBody += '<tr>';
		for (var columnIndex=0; columnIndex<columns; columnIndex++) {
			var id = '' + rowIndex + '-' + columnIndex;
			//tableBody += '<td style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" id="';
			//tableBody += '<td style="padding-right:50px;" id="';
			tableBody += '<td id="';
			tableBody += id;
			tableBody += '">';
			tableBody += '</td>'; 
		}
		tableBody += '</tr>';
	}
	
	document.getElementById('list_table').getElementsByTagName('thead').item(0).innerHTML = tableHead;
	document.getElementById('list_table').getElementsByTagName('tbody').item(0).innerHTML = tableBody;
}

function setTitle(text, number) {
	document.getElementsByTagName("head").item(0).getElementsByTagName("title").item(0).innerHTML = "PrivacyScore - Scan - " + text + " - " + getDate(number, langData.timeFormat, langData.dateFormat);
}

function setHeader1(text) {
	document.getElementById("header1").innerHTML = text;
}

function setDate(startdate, enddate) {
	document.getElementById("startdate").innerHTML = getDate(startdate, langData.timeFormat, langData.dateFormat);
	if (enddate != "-1") {
		document.getElementById("enddate").innerHTML = getDate(enddate, langData.timeFormat, langData.dateFormat);
	}
}

function setDescription(text) {
	document.getElementById("description").innerHTML = text;
}

function setTags(text) {
	document.getElementById("tags").innerHTML = text.toString().replace(/,/g,", ");
}

function setThirdPartiesButton(list, group) {
	document.getElementById("popularThirdPartiesButton").href = "thirdParties.html?lang=" + langData.lang + "&list=" + list + "&group=" + group;;
}

function setDashboard(data) {
	
	var dashboard = document.getElementById("dashboard");
	
	// calculate average score
	var sum = 0;
	for (var i = 0; i<data.length; i++) {
		if (data[i].scans.length>0) {
			sum += data[i].scans[0].score.charCodeAt(0);
		}
	}
	var average = Math.floor(sum/data.length);
	dashboard.getElementsByClassName("col-md-3").item(0).getElementsByTagName("div").item(0).innerHTML = String.fromCharCode(average);
	
	// calculate percentage of sites with https
	var sum = 0;
	for (var i = 0; i<data.length; i++) {
		if (data[i].scans.length>0 && data[i].scans[0].https) {
			sum++;
		}
	}
	dashboard.getElementsByClassName("col-md-3").item(1).getElementsByTagName("div").item(0).innerHTML = Math.round((sum*100/data.length)*100)/100 + "%";
	
	// calculate average number of cookies
	sum = 0;
	for (var i = 0; i<data.length; i++) {
		if (data[i].scans.length>0) {
			sum += data[i].scans[0].cookies_anzahl;
		}
	}
	average = sum/data.length;
	dashboard.getElementsByClassName("col-md-3").item(2).getElementsByTagName("div").item(0).innerHTML = Math.round(average*100)/100;
	
	// calculate average number of third parties
	sum = 0;
	for (var i = 0; i<data.length; i++) {
		if (data[i].scans.length>0) {
			sum += data[i].scans[0].third_parties_anzahl;
		}
	}
	average = sum/data.length;
	
	dashboard.getElementsByClassName("col-md-3").item(3).getElementsByTagName("div").item(0).innerHTML = Math.round(average*100)/100;
}

function setScanButton(last_scan) {
	var date = new Date(Date.parse(last_scan));
	
	var difference = Date.now() - Date.parse(last_scan);
	var minutes = Math.floor((difference)/60000);
	//minutes = minutes	+ date.getTimezoneOffset();	// convert from GMT to GMT+1
	// if last scan was less than 30 minutes ago
	if (isNaN(minutes)) {
		document.getElementById("scan_again").className += " disabled";
		document.getElementById("scan_again").innerHTML = langData.scannedList.buttonsScanning.scan_again_scanning;
	} else if (minutes<30) {
		document.getElementById("scan_again").className += " disabled";
		var inMinutes = 30 - minutes;
		document.getElementById("scan_again").innerHTML = langData.scannedList.buttonsScanning.scan_again_later.replace("#M", inMinutes);
	}
}

function setNewListButton(id, group) {
	document.getElementById("new_list").href += "?list=" + id + "&group=" + group + "&n=true";
}

function createTableHeadContent(json) {
	var tableHeadContent = [];
	tableHeadContent.push("URL");
	for (var i=0; i<json.columns.length; i++) {
		tableHeadContent.push(json.columns[i].name);
	}
	for (var i=0; i<resultColumns.length; i++) {
		tableHeadContent.push(resultColumns[i]);
	}
	return tableHeadContent;
}

function createTableBody(json) {
	var tableBody = [];
	
	for (var rowIndex=0; rowIndex<json.seiten.length; rowIndex++) {
		var row = [];
		// add url and id for first column
		var scan_id = "";
		var side_id = "";
		if (json.seiten[rowIndex].scans.length > 0) {
			scan_id = json.seiten[rowIndex].scans[0]._id.$oid;
			site_id = json.seiten[rowIndex]._id.$oid;
		}
		var helpObject = {"url": json.seiten[rowIndex].url, "site_id": site_id, "scan_id": scan_id}
		row.push(helpObject);
		for (var columnIndex=0; columnIndex<json.seiten[rowIndex].column_values.length; columnIndex++) {
			row.push(json.seiten[rowIndex].column_values[columnIndex]);
		}
		// add the results to the row
		if (json.seiten[rowIndex].scans.length > 0) {
			row.push(json.seiten[rowIndex].scans[0].score);
			row.push(json.seiten[rowIndex].scans[0].https);
			row.push(json.seiten[rowIndex].scans[0].redirected_to_https);
			row.push(json.seiten[rowIndex].scans[0].cookies_anzahl);
			row.push(json.seiten[rowIndex].scans[0].third_parties_anzahl);
			row.push(json.seiten[rowIndex].scans[0].third_party_requests_anzahl);
			row.push(json.seiten[rowIndex].scans[0].geoip_all_webservers_in_germany);
			var hsts = false;
			for (var i=0; i<json.seiten[rowIndex].scans[0].headerchecks.length; i++) {
				if (json.seiten[rowIndex].scans[0].headerchecks[i].hasOwnProperty("key") && json.seiten[rowIndex].scans[0].headerchecks[i].key == "hsts" && json.seiten[rowIndex].scans[0].headerchecks[i].status.toLowerCase() == "ok") {
					hsts = true;
				}
			}
			row.push(hsts);
		}
		tableBody.push(row);
	}
	return tableBody;
}

function setOldNewScans(scanJson, list, group) {
	$.get(apiUrl + "GetScanGroupsByList/" + list, function (jsonString) {
		//jsonString = jsonString.replace(/'/g, '"');
		oldNewData = JSON.parse(jsonString);
		console.log(oldNewData);
		if (oldNewData == null) {
			
		} else {
			
			
		console.log(oldNewData);
		html = '';
		var otherScans = oldNewData;
		
		// hide the diagram buttons if no other scans
		if (otherScans.length<2) {
			var elements = document.getElementsByClassName("fa-line-chart");
			for (var i=0; i<elements.length; i++) {
				elements[i].style.display = "none";
			}
		}
		
		for (var i=otherScans.length-1; i>=0; i--) {
			if (otherScans[i]._id.$oid == group) {
				html += '<option selected="selected" value="#">';
				html += getDate(otherScans[i].startdate, langData.timeFormat, langData.dateFormat);
				html += '</option>';
				// set scan date below description
				setDate(oldNewData[i].startdate, oldNewData[i].enddate);
			} else {
				html += '<option value="scannedList.html?lang=' + langData.lang + '&list=';
				html += list;
				html += '&group=';
				html += otherScans[i]._id.$oid;
				html += '">';
				html += getDate(otherScans[i].startdate, langData.timeFormat, langData.dateFormat);
				html += '</option>';
			}
		}
		document.getElementById("oldNewScans").innerHTML = html;
		setScanButton(otherScans[otherScans.length-1].enddate);
		
		// check if newest scan is state == finish
		if ((oldNewData[oldNewData.length-1].state != "finish")) {
			console.log(global_group);
			$.get(apiUrl + "ShowScannedList/" + getUrlVars()["list"] + "/" + getUrlVars()["group"], function (jsonString) {
			json = JSON.parse(jsonString);
			if (json == null) {
				document.getElementsByTagName("content").item(0).innerHTML = "<br>" + langData.scannedList.alerts.noListFoundID.replace("#ID", listid);
			} else {
				console.log(oldNewData);
				//refresh after 5 seconds
				if (getUrlVars()["group"] == oldNewData[oldNewData.length-1]._id.$oid && oldNewData.length>0 && oldNewData[0].hasOwnProperty("progress") && oldNewData[0].hasOwnProperty("progress_timestamp")) {
					var startdate = getDate(oldNewData[oldNewData.length-1].startdate, langData.timeFormat, langData.dateFormat);
					var  html = '<i class="fa fa-exclamation-triangle"></i> ' + langData.scannedList.progress.progress1.replace("#TIME", startdate);
					html += "<br>" + langData.scannedList.progress.status + ": " + oldNewData[oldNewData.length-1].progress;
					//var time = Date(oldNewData[oldNewData.length-1].progress_timestamp_absolute);
					html += "<br>" + oldNewData[oldNewData.length-1].progress_timestamp;
					document.getElementById("loadingProgress").innerHTML = html;
					document.getElementById("compareDiv").style.display = "none";
					document.getElementById("dashboard").style.display = "none";
					
					document.getElementById("listScanning").style.display = "block";
					document.getElementById("listScanning").innerHTML = html;
					setHeader1(json.name);
					setTitle(json.name, oldNewData[oldNewData.length-1].startdate);
					setDescription(json.description);
					setTags(json.tags);
					setDate(oldNewData[0].startdate, "-1");
					//setTimeout(function(){location.reload()}, 5000);
				}
			}
        });
		
		}
		

		
		}
	});
	
	
	
}

function setCompareScans(list, group) {
	$.get(apiUrl + "GetScanGroupsByList/" + list, function (jsonString) {
		//jsonString = jsonString.replace(/'/g, '"');
		data = JSON.parse(jsonString);
		console.log(data);
		if (data == null) {
			
		} else {
			
			// delete scans that are not state == "finish"
			var helpData = [];
			for (var i=0; i<data.length; i++) {
				if (data[i].state == "finish") {
					helpData.push(data[i]);
				}
			}
			data = helpData;
			
			console.log(data);
			
			if (data.length>1) {
			
				html = '';
				var otherScans = data;
				
				for (var i=otherScans.length-1; i>=0; i--) {
					if (otherScans[i]._id.$oid == group) {
						//html += '<option selected="selected" value="#">';
						//html += getDate(otherScans[i].startdate);
						//html += '</option>';
						// set scan date below description
						//setDate(data[i].startdate, data[i].enddate);
					} else {
						html += '<option value="';
						html += list;
						html += '/';
						html += otherScans[i]._id.$oid;
						html += '">';
						html += getDate(otherScans[i].startdate, langData.timeFormat, langData.dateFormat);
						html += '</option>';
					}
				}
				document.getElementById("compareScans").innerHTML = html;
				//setScanButton(otherScans[otherScans.length-1].enddate);
				
				// check if newest scan is state == finish
				if ((getUrlVars()["group"] == data[data.length-1]._id.$oid) && (data[data.length-1].state != "finish") && (group == "")) {
					var startdate = getDate(data[data.length-1].startdate, langData.timeFormat, langData.dateFormat);
					document.getElementById("listScanning").style.display = "block";
					document.getElementById("listScanning").innerHTML = '<i class="fa fa-exclamation-triangle"></i> Scan läuft seit ' + startdate;
					
				}
				
				fillDiagramSettings(listData, data);
				
			} else {
				document.getElementById("compareDiv").style.display = "none";
			}
		}
	});
	
	
	
}


function calculateHeight(rows) {
	var height = Math.min($(window).height()-300,rows*40);
	var maxHeight = $(window).height()-200;
	if (maxHeight > rows*42) {
		height = rows*45 + 5;
	} else {
		height = maxHeight;
	}
	return height+20;
}

function scanAgain() {
	var req = {"listid": global_list_id};
	$.ajax({
		url: apiUrl + '/ScanList',
		type: 'POST',
		data: JSON.stringify(req),
		headers: {
			'Content-Type': 'application/json; charset=utf-8;'
		},
		success: function (jsonString) {
			console.log(jsonString);
			data = JSON.parse(jsonString);
			if (data == null || (data.hasOwnProperty("type") && data.type == "error")) {
				alert(langData.scannedList.alerts.scanStartedError);
			} else {
				alert(langData.scannedList.alerts.scanStarted);
			}
			window.location.reload();
		}
	});

}

function expandList(showall) {
	window.location.href = "scannedList.html?list=" + global_list_id + "&group=" + global_group + "&showall=" + !showall + "&lang=" + langData.lang;
}

function toggleCompare() {
	var checkBox = document.getElementById("compareCheckbox");
	if (checkBox.checked) {
		var dropdown = document.getElementById("compareScans");
		var value = dropdown.options[dropdown.selectedIndex].value.split("/");
		getCompareData(value[0], value[1]);
		document.getElementById("comparedDates").style.display = "block";
	} else {
		// set page length to max (to fill the table)
		var table = $('#list_table').DataTable();
		var oldLen = table.page.len();
		table.page.len(-1).draw();
		// set back to original data
		fillTable(createTableHeadContent(listData), createTableBody(listData), oldLen);
		document.getElementById("comparedDates").style.display = "none";
	}
}

function dropdownAction() {
	var checkBox = document.getElementById("compareCheckbox");
	if (checkBox.checked) {
		var dropdown = document.getElementById("compareScans");
		var value = dropdown.options[dropdown.selectedIndex].value.split("/");
		getCompareData(value[0], value[1]);
	}
}

function getCompareData(list, group) {
	document.getElementById("listScanning").innerHTML = "";
	var loader = document.getElementById("loader");
	loader.style.display = "block";
	var param = list + "/" + group;
	$.get(apiUrl + "ShowScannedList/" + param, function (jsonString) {
		data = JSON.parse(jsonString);
		if (data == null) {
			document.getElementsByTagName("content").item(0).innerHTML =  "<br>" + langData.scannedList.alerts.noListFoundID.replace("#ID", listid);
		} else {
			displayCompare(data);
		}
		loader.style.display = "none";
    });
}

function displayCompare(json) {
	// set page length to max (to fill the table)
	var table = $('#list_table').DataTable();
	var oldLen = table.page.len();
	table.page.len(-1).draw();
	
	console.log(json);
	var scoreColumnIndex = json.seiten[0].column_values.length + 1;	//+1 for url
	var httpsColumnIndex = scoreColumnIndex + 1;
	var httpsRedirectColumnIndex = httpsColumnIndex + 1;
	var cookiesColumnIndex = httpsRedirectColumnIndex + 1;
	
	var firstColumnIndex = json.seiten[0].column_values.length + 1;	//+1 for url
	console.log(firstColumnIndex);
	for (var row=0; row<json.seiten.length; row++) {
		var maxIndex = json.seiten.length + resultColumns.length - 1;
		// create an old_data array for this row
		var oldData = [];
		oldData.push(listData.seiten[row].scans[0].score);
		oldData.push(listData.seiten[row].scans[0].https);
		oldData.push(listData.seiten[row].scans[0].redirected_to_https);
		oldData.push(listData.seiten[row].scans[0].cookies_anzahl);
		oldData.push(listData.seiten[row].scans[0].third_parties_anzahl);
		oldData.push(listData.seiten[row].scans[0].third_party_requests_anzahl);
		oldData.push(listData.seiten[row].scans[0].geoip_all_webservers_in_germany);
		var hsts = false;
		for (var i=0; i<listData.seiten[row].scans[0].headerchecks.length; i++) {
			if (listData.seiten[row].scans[0].headerchecks[i].hasOwnProperty("key") && listData.seiten[row].scans[0].headerchecks[i].key == "hsts" && listData.seiten[row].scans[0].headerchecks[i].status.toLowerCase() == "ok") {
				hsts = true;
			}
		}
		oldData.push(hsts);
				
		// create a new_data array for this row
		var newData = [];
		newData.push(json.seiten[row].scans[0].score);
		newData.push(json.seiten[row].scans[0].https);
		newData.push(json.seiten[row].scans[0].redirected_to_https);
		newData.push(json.seiten[row].scans[0].cookies_anzahl);
		newData.push(json.seiten[row].scans[0].third_parties_anzahl);
		newData.push(json.seiten[row].scans[0].third_party_requests_anzahl);
		newData.push(json.seiten[row].scans[0].geoip_all_webservers_in_germany);
		var hsts = false;
		for (var i=0; i<json.seiten[row].scans[0].headerchecks.length; i++) {
			if (json.seiten[row].scans[0].headerchecks[i].hasOwnProperty("key") && json.seiten[row].scans[0].headerchecks[i].key == "hsts" && json.seiten[row].scans[0].headerchecks[i].status.toLowerCase() == "ok") {
				hsts = true;
			}
		}
		newData.push(hsts);
		
		
		// get the dates from both datas
		var oldDate = listData.seiten[row].scans[0].starttime;
		oldDate = new Date(oldDate);
		var newDate = json.seiten[row].scans[0].starttime;
		newDate = new Date(newDate);
		
		// sort the both compared datasets and set the displayed dates above the table
		var dateHTML = langData.scannedList.comparedScans.dateLine;
		if (oldDate>newDate) {
			[oldDate, newDate] = [newDate, oldDate];
			[oldData, newData] = [newData, oldData];
			dateHTML = dateHTML.replace("#NEWDATE", getDate(listData.seiten[row].scans[0].starttime, langData.timeFormat, langData.dateFormat));
			dateHTML = dateHTML.replace("#OLDDATE", getDate(json.seiten[row].scans[0].starttime, langData.timeFormat, langData.dateFormat));
			// document.getElementById("newDate").innerHTML = getDate(listData.seiten[row].scans[0].starttime, langData.timeFormat, langData.dateFormat);
			// document.getElementById("oldDate").innerHTML = getDate(json.seiten[row].scans[0].starttime, langData.timeFormat, langData.dateFormat);
		} else {
			dateHTML = dateHTML.replace("#OLDDATE", getDate(listData.seiten[row].scans[0].starttime, langData.timeFormat, langData.dateFormat));
			dateHTML = dateHTML.replace("#NEWDATE", getDate(json.seiten[row].scans[0].starttime, langData.timeFormat, langData.dateFormat));
		}
		document.getElementById("comparedDates").innerHTML = "<small>" + dateHTML + "</small>";
		
		// compare with for loop
		for (var dataIndex=0; dataIndex<oldData.length; dataIndex++) {
			var id = firstColumnIndex + dataIndex;
			id = "" + row + "-" + id;
			var html = "";
			// set old data
			if (typeof(oldData[dataIndex]) == "boolean" && oldData[dataIndex]) {
				html += '<span class="glyphicon glyphicon-ok"><span style="display:none">false</span></span>';
			} else if (typeof(oldData[dataIndex]) == "boolean" && !oldData[dataIndex]) {
				html += '<span class="glyphicon glyphicon-remove"><span style="display:none">false</span></span>';
			} else {
				html += oldData[dataIndex];
			}
			// set compare arrow
			if (oldData[dataIndex] > newData[dataIndex]) {
				html += '<i class="fa fa-long-arrow-right fa-rotate-down" style="color:green;"></i>';
			} else if (oldData[dataIndex] < newData[dataIndex]) {
				html += '<i class="fa fa-long-arrow-right fa-rotate-up" style="color:red;"></i>';
			} else {
				html += '<i class="fa fa-long-arrow-right"></i>';
			}
			// set new data
			if (typeof(newData[dataIndex]) == "boolean" && newData[dataIndex]) {
				html += '<span class="glyphicon glyphicon-ok"><span style="display:none">false</span></span>';
			} else if (typeof(newData[dataIndex]) == "boolean" && !newData[dataIndex]) {
				html += '<span class="glyphicon glyphicon-remove"><span style="display:none">false</span></span>';
			} else {
				html += newData[dataIndex];
			}			
			document.getElementById(id).innerHTML = html;
		}
	}
	// set the old page length
	table.page.len(oldLen).draw();
}

function fillDiagramSettings(scanJson, otherScans) {
	//document.getElementById("showDiagramBox").style.display = "block";
	// console.log(1);
	// console.log(scanJson);
	// console.log(otherScans);
		
	var div_scandates = document.getElementById("diagram-box-settings-scandate");
	
	var html = "";
	
	for (var i=otherScans.length-1; i>=0; i--) {
		html += '<div class="checkbox">';
		html += '<label><input ';
		if (i > otherScans.length-4) {
			html += 'checked ';
		}
		html += 'type="checkbox" ';
		html += 'id="group-' + i + '" ';
		html += 'value="';
		html += otherScans[i]._id.$oid;
		html +='">';
		html += getDate(otherScans[i].startdate, langData.timeFormat, langData.dateFormat);
		html += '</label>';
		html += '</div>';
	}
	
	div_scandates.innerHTML = html;
	
	
	
}

function closeDiagram() {
	document.getElementById("diagram-box").style.display = "none";
	//document.getElementById("overlay").style.display = "none";
}

function openDiagram() {
	document.getElementById("diagram-box").style.display = "block";
	$('.collapse').collapse("show")
	//document.getElementById("overlay").style.display = "block";
}

function submitDiagram() {
	var groupsLength = document.getElementById("diagram-box-settings-scandate").getElementsByClassName("checkbox").length;

	var selectedGroups = 0;
	for (var i=0; i<groupsLength; i++) {
		var id = "group-" + i;
		if (document.getElementById(id).checked) {
			selectedGroups++;
		}
	}
	
	// var max = 5;
	// if (selectedGroups>max) {
		// alert("Bitte wählen Sie maximal " + max + " Scans aus!");
	// } else if (selectedGroups<2) {
		// alert("Bitte wählen Sie mindestens zwei Scans aus!");
	// } else {
		// document.getElementById("diagram").innerHTML = "";
		// loadDiagram();
		// $('.collapse').collapse("toggle")
	// }
	
	document.getElementById("diagram").innerHTML = "";
	loadDiagram();
	
}

function openAndLoadDiagram(site_id) {
	global_diagram_site = site_id;
	openDiagram();
	document.getElementById("diagram").innerHTML = "";
	loadDiagram(site_id);
	scrollToTop();
	$('.collapse').collapse("hide")
}

function deleteList() {
	if (confirm(langData.list.confirms.deleteList)) {
		var listid = getUrlVars()["list"];
			$.ajax({
				url: apiUrl + '/GetToken/' + listid,
				type: 'POST',
				xhrFields: {
					withCredentials: true
				},
				success: function (data) {
					data = JSON.parse(data);
				$.get(apiUrl + "/DeleteList/" + data.token + '/', function (jsonString) {
					var data = JSON.parse(jsonString);
					console.log(data);
					var lang = getUrlVars()["lang"];
					window.location.href = "index.html?lang=" + lang;
					
				});
				}
			});
		
		
		
	} else {
		//alert("Die Liste wurde nicht gelöscht.");
		alert(langData.list.alerts.notDeleted);
	}
}

function setDeleteButton(userid) {
	var isAdmin = false;
	if (getCookie("isAdmin") != null && getCookie("isAdmin") == "true") {
		isAdmin = true;
	}
	if (getCookie("userid") == userid || isAdmin) {
		document.getElementById("delete_list").style.display = "block";
	}
}
