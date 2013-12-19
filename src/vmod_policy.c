#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <arpa/inet.h>

#include "vrt.h"
#include "vsb.h"
#include "cache/cache.h"

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

VCL_INT
vmod_check(const struct vrt_ctx *ctx, VCL_STRING socketfile, VCL_REAL timeout) {
	char *p, *q;
	int u, v;
	char hdrname[1000];
	int i, hdrnamelen, sock, s;
	struct vsb *meta, *headers;
	struct sockaddr_un serveraddr;
#define SERVERADDR_MAX 254
	ssize_t len;
	char vpolhdr[] = "VPOL01";
	char response[] = "000\0";
	short responsecode;

	AN(socketfile);
	AN(timeout);

	memset(&serveraddr, 0, sizeof(struct sockaddr_un));
	serveraddr.sun_family = AF_UNIX;
	strncpy(serveraddr.sun_path, socketfile, strlen(socketfile));

	sock = socket(AF_UNIX, SOCK_STREAM, 0);
	if (sock == -1) {
		VSL(SLT_VCL_Log, 0, "socket(): %i %s", sock, strerror(sock));
		return EXIT_ERR;
	}
	s = connect(sock, (struct sockaddr *)&serveraddr, sizeof(struct sockaddr_un));
	if (s != 0) {
		VSL(SLT_VCL_Log, 0, "connect(): (%i) %s", errno, strerror(errno));
		return EXIT_ERR;
	}
	AN(sock);

	meta = VSB_new_auto();
	VSB_printf(meta, "xid: %i\n", ctx->req->sp->vxid);
	VSB_printf(meta, "vcl_method: %i\n", ctx->req->wrk->cur_method);
	VSB_printf(meta, "client_identity: %s\n", ctx->req->client_identity);
	VSB_printf(meta, "t_open: %i\n", ctx->req->sp->t_open);
	VSB_printf(meta, "http_method: %s\n", ctx->req->http->hd[0].b);
	VSB_printf(meta, "URL: %s\n", ctx->req->http->hd[1].b);
	VSB_printf(meta, "proto: %s\n", ctx->req->http->hd[2].b);
	VSB_finish(meta);

	headers = VSB_new_auto();
	for (u = HTTP_HDR_FIRST; u < ctx->req->http->nhd; u++) {
		VSB_bcat(headers, ctx->req->http->hd[u].b, Tlen(ctx->req->http->hd[u]));
		VSB_cat(headers, "\n");
	}
	VSB_finish(headers);

	// VSL(SLT_Debug, 0, "headers: (%i) %s ", VSB_len(headers), VSB_data(headers));
	// format and send the VPOL header.
	send(sock, &vpolhdr, sizeof(vpolhdr)-1, 0);

	// VSL(SLT_VCL_Log, 0, "meta len is: %i", VSB_len(meta));
	len = htonl(VSB_len(meta));
	send(sock, &len, sizeof(uint32_t), 0);

	len = htonl(VSB_len(headers));
	send(sock, &len, sizeof(uint32_t), 0);

	len = 0; // no body
	send(sock, &len, sizeof(uint32_t), 0);

	// send the content.
	send(sock, VSB_data(meta), VSB_len(meta), 0);
	send(sock, VSB_data(headers), VSB_len(headers), 0);

	// read and parse the response.
	s = recv(sock, &response, sizeof(response), 0);

	if (s == -1) {
		VSL(SLT_VCL_Log, 0, "recv(): %s", strerror(s));
		close(sock);
		return EXIT_ERR;
	}
	close(sock);

	responsecode = atoi((const char *)&response);
	if (responsecode == 200) {
		return EXIT_OK;
	}
	// VSL(SLT_VCL_Log, 0, "responsecode: %i", responsecode);
	return EXIT_NO;
}
