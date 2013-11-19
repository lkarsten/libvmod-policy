#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <sys/socket.h>
#include <netdb.h>

#include "vrt.h"
#include "vsb.h"
#include "bin/varnishd/cache.h"

#include "vcc_if.h"

// such pretty return values.
#define EXIT_OK 0
#define EXIT_NO -1
#define EXIT_ERR 3

int
init_function(struct vmod_priv *priv, const struct VCL_conf *conf)
{
	return (0);
}



int
vmod_check(struct sess *sp, const char *destip, const char *port) {
	char *p, *q;
	int u, v;
	char hdrname[1000];
	int i, hdrnamelen, sock;
	struct vsb *meta, *headers;
	struct addrinfo hints, *rp;

	AN(destip);
	AN(port);

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
//	VSL(SLT_Debug, 0, "vsb is: %s", VSB_data(fp));

	sock = socket(AF_INET, SOCK_STREAM, 0);
	if (!sock) { return EXIT_ERR; }

	// please, just fix this sockaddr mess for me.

	memset(&hints, 0, sizeof(struct addrinfo));
	hints.ai_flags = AI_NUMERICHOST; // no DNS resolving, must be an IP.
	int s = getaddrinfo(destip, port, &hints, &rp);
	if (!s) { return EXIT_ERR; }
	AN(rp);

	s = connect(sock, rp->ai_addr, rp->ai_addrlen);
	if (!s) { return EXIT_ERR; }

	int n = 0;
	char msg[1024] = "\0";
	size_t len = sprintf(msg, "VPOL%i%i%l", &n, &n, &n);
	send(sock, &msg, len, 0);
	//VSB_data(meta));
	send(sock, VSB_data(meta), VSB_len(meta), 0);
	send(sock, VSB_data(headers), VSB_len(meta), 0);

	char res[] = "NO";
	n = recv(sock, &res, 2, 0);
	if (!n) { return EXIT_ERR; }

	//if (strncmp(&res, "OK", 2) == 0) {
//		return EXIT_OK;
//	} else return EXIT_NO;
	return EXIT_ERR;
}
