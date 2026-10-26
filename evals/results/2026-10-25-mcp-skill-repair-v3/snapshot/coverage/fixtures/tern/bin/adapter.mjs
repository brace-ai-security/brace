import {startProxy} from '@sample/mcp-runtime';
const token = process.env.ACCESS_TOKEN;
if (!token) throw new Error('missing token');
startProxy({endpoint: 'https://ledger.example.test/mcp', headers: {Authorization: `Bearer ${token}`}});
