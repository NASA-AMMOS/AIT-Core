var express = require('express');

function StaticServer() {
    var router = express.Router();

    router.use('/', express.static(__dirname + '/.'));

    return router
}

var expressWs = require('express-ws');
var app = express();

expressWs(app);

var staticServer = new StaticServer();
app.use('/', staticServer);

var port = process.env.PORT || 8080

app.listen(port, function () {
    console.log('Open MCT hosted at http://localhost:' + port);
});

