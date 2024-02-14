anychart.onDocumentReady(function() {
//console.log({{svtdetails}});
// set the data
var data = [
  {x: "DEV Servers", value: 50},
  {x: "OSS Servers", value: 30},
  {x: "QAE Servers", value: 20},
  {x: "COMMON Servers", value: 4},
  {x: "OTHERS Servers", value: 10}

];





// create the chart
var chart = anychart.pie();

// set the chart title
chart.title("PeopleSoft Enviornment Dashboard: Server Inventory");

// add the data
chart.data(data);

// set legend position
chart.legend().position("right");
// set items layout
chart.legend().itemsLayout("vertical");

// display the chart in the container
chart.container('container');
chart.draw();

});
