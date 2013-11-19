#include <stdlib.h>
#include <string.h>
#include <socket.h>

#include "vrt.h"
#include "vsb.h"
#include "bin/varnishd/cache.h"

#include "vcc_if.h"

int
init_function(struct vmod_priv *priv, const struct VCL_conf *conf)
{
	return (0);
}


float
vmod_check(struct sess *sp, const char * dest) {
	char *p, *q;
	char hdrname[1000];
	int i, hdrnamelen;
	unsigned u, v;

	struct vsb *meta, *headers;
	meta = VSB_new_auto();
	VSB_cat(meta, "x-foo: bar");

	headers = VSB_new_auto();
	for (u = HTTP_HDR_FIRST; u < sp->http->nhd; u++) {
		q = index(sp->http->hd[u].b, ':');
		if (q == NULL) continue;

		// TODO: fix this buffering
		hdrnamelen = q - sp->http->hd[u].b;
		strncpy(hdrname, sp->http->hd[u].b, hdrnamelen);
		/*if (u > HTTP_HDR_FIRST)
			VSB_cat(fp, "__");
			*/
		VSB_bcat(headers, hdrname, hdrnamelen);
	}
	VSB_finish(meta);
	VSB_finish(headers);
	VSL(SLT_Debug, 0, "vsb is: %s", VSB_data(fp));

	sock = socket(AF_INET, SOCK_DGRAM);
	fd = sock.connect("127.0.0.1", 15696);
	if (!fd) {
		return "NO";


	v++;
	u = WS_Reserve(sp->wrk->ws, 0);
	p = sp->wrk->ws->f;
	if (v > u) {
		WS_Release(sp->wrk->ws, 0);
		return (NULL);
	}
	strcpy(p, VSB_data(fp));

	WS_Release(sp->wrk->ws, v);
	return (p);
}
