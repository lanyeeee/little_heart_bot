const express = require('express');
const bodyParser = require('body-parser')
const {program} = require('commander');
const log = require('./app/util/LogHelper')
const common = require('./app/util/common')
const client = require('./app/util/client')
const encrypt = require('./app/controller/encrypt')
const app = express();
log.LogHelper.Init();

// commandline arguments
function parsePort(defaultPort) {
    program.version('0.0.1');
    program
        .version('0.0.1')
        .usage('[options] [value ...]')
        .option('-p, --port <number>', 'port', common.myParseInt)
    program.parse(process.argv);
    const options = program.opts();
    if (options.port === undefined) {
        return defaultPort;
    }
    return options.port;
}

// CORS & Preflight request
app.use((req, res, next) => {
    if (req.path !== '/' && !req.path.includes('.')) {
        res.set({
            'Access-Control-Allow-Credentials': true,
            'Access-Control-Allow-Origin': req.headers.origin || '*',
            'Access-Control-Allow-Headers': 'X-Requested-With,Content-Type',
            // 'Access-Control-Allow-Methods': 'PUT,POST,GET,DELETE,OPTIONS',
            'Access-Control-Allow-Methods': 'POST,GET',
            'Content-Type': 'application/json; charset=utf-8',
        })
    }
    req.method === 'OPTIONS' ? res.status(204).end() : next()
})

// middleware .body parser
app.use(client(), bodyParser.json(), bodyParser.urlencoded({extended: false}));

app.get('/enc', (request, response) => {
    encrypt.handleGetEncrypt(request, response)
});
app.post('/enc', (request, response) => {
    encrypt.handlePostEncrypt(request, response)
});

// start api server
const port = parsePort(3000)
app.listen(port || process.env.PORT, () => {
    // console.info(`server now listening at port ${port}`);
    console.info(`server running @ http://0.0.0.0:${port}`)
});

