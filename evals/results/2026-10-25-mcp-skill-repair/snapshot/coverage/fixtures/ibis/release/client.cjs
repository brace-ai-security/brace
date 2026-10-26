exports.read = async function(args, token) {
  if (!Number.isInteger(args.limit) || args.limit < 1 || args.limit > 20) throw new RangeError('limit');
  const res = await fetch(`https://ledger.example.test/entries?limit=${args.limit}`, {
    headers: {Authorization: `Bearer ${token}`}, redirect: 'error'
  });
  if (!res.ok) throw new Error('backend status');
  return await res.json();
};
