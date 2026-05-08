import io.netty.bootstrap.Bootstrap;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInboundHandlerAdapter;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.ChannelOption;
import io.netty.channel.ChannelPipeline;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioSocketChannel;

import java.net.InetSocketAddress;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

public class MinimalConcurrentNettyHandshakeClient {
    private static byte[] hexToBytes(String hex) {
        String normalized = hex.replaceAll("\\s+", "");
        if ((normalized.length() & 1) != 0) {
            throw new IllegalArgumentException("hex length must be even");
        }
        byte[] out = new byte[normalized.length() / 2];
        for (int i = 0; i < out.length; i++) {
            int hi = Character.digit(normalized.charAt(i * 2), 16);
            int lo = Character.digit(normalized.charAt(i * 2 + 1), 16);
            if (hi < 0 || lo < 0) {
                throw new IllegalArgumentException("invalid hex digit");
            }
            out[i] = (byte) ((hi << 4) | lo);
        }
        return out;
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 4 || args.length > 5) {
            System.err.println("usage: MinimalConcurrentNettyHandshakeClient <host> <port> <request_hex> <concurrency> [timeout_ms]");
            System.exit(2);
        }

        String host = args[0];
        int port = Integer.parseInt(args[1]);
        byte[] request = hexToBytes(args[2]);
        int concurrency = Integer.parseInt(args[3]);
        long timeoutMs = args.length == 5 ? Long.parseLong(args[4]) : 1000L;

        long startedAt = System.currentTimeMillis();
        AtomicInteger connectFinished = new AtomicInteger();
        AtomicInteger channelActive = new AtomicInteger();
        AtomicInteger writeSubmitted = new AtomicInteger();
        AtomicInteger writeSuccess = new AtomicInteger();
        AtomicInteger readObserved = new AtomicInteger();
        AtomicInteger bytesWritten = new AtomicInteger();
        AtomicInteger bytesRead = new AtomicInteger();
        AtomicInteger timeoutClose = new AtomicInteger();
        AtomicInteger exceptionCount = new AtomicInteger();
        CountDownLatch done = new CountDownLatch(concurrency);
        List<String> exceptionClasses = new ArrayList<>();
        Object exceptionLock = new Object();

        NioEventLoopGroup group = new NioEventLoopGroup(1);
        try {
            Bootstrap bootstrap = new Bootstrap();
            bootstrap.group(group)
                .channel(NioSocketChannel.class)
                .option(ChannelOption.TCP_NODELAY, true)
                .handler(new ChannelInitializer<SocketChannel>() {
                    @Override
                    protected void initChannel(SocketChannel ch) {
                        ChannelPipeline pipeline = ch.pipeline();
                        pipeline.addLast(new ChannelInboundHandlerAdapter() {
                            private volatile boolean finished;

                            private void finishOnce() {
                                if (!finished) {
                                    finished = true;
                                    done.countDown();
                                }
                            }

                            @Override
                            public void channelActive(ChannelHandlerContext ctx) {
                                channelActive.incrementAndGet();
                                ByteBuf buf = Unpooled.wrappedBuffer(request.clone());
                                bytesWritten.addAndGet(buf.readableBytes());
                                writeSubmitted.incrementAndGet();
                                ctx.executor().schedule(() -> {
                                    if (!finished) {
                                        timeoutClose.incrementAndGet();
                                        finishOnce();
                                        ctx.close();
                                    }
                                }, timeoutMs, TimeUnit.MILLISECONDS);
                                ctx.writeAndFlush(buf).addListener(future -> {
                                    if (future.isSuccess()) {
                                        writeSuccess.incrementAndGet();
                                    } else {
                                        exceptionCount.incrementAndGet();
                                        synchronized (exceptionLock) {
                                            Throwable t = future.cause();
                                            exceptionClasses.add(t == null ? "write_failure" : t.getClass().getName());
                                        }
                                        finishOnce();
                                    }
                                });
                            }

                            @Override
                            public void channelRead(ChannelHandlerContext ctx, Object msg) {
                                readObserved.incrementAndGet();
                                ByteBuf buf = (ByteBuf) msg;
                                try {
                                    bytesRead.addAndGet(buf.readableBytes());
                                } finally {
                                    buf.release();
                                }
                                finishOnce();
                                ctx.close();
                            }

                            @Override
                            public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
                                exceptionCount.incrementAndGet();
                                synchronized (exceptionLock) {
                                    exceptionClasses.add(cause.getClass().getName());
                                }
                                finishOnce();
                                ctx.close();
                            }
                        });
                    }
                });

            List<ChannelFuture> futures = new ArrayList<>();
            for (int i = 0; i < concurrency; i++) {
                ChannelFuture future = bootstrap.connect(new InetSocketAddress(host, port)).sync();
                if (future.isSuccess()) {
                    connectFinished.incrementAndGet();
                }
                futures.add(future);
            }

            done.await(timeoutMs + 1500L, TimeUnit.MILLISECONDS);
            for (ChannelFuture future : futures) {
                future.channel().close().syncUninterruptibly();
            }
        } finally {
            group.shutdownGracefully().syncUninterruptibly();
        }

        long finishedAt = System.currentTimeMillis();
        System.out.println("{");
        System.out.println("  \"host\": \"" + host + "\",");
        System.out.println("  \"port\": " + port + ",");
        System.out.println("  \"concurrency\": " + concurrency + ",");
        System.out.println("  \"timeout_ms\": " + timeoutMs + ",");
        System.out.println("  \"connect_finished\": " + connectFinished.get() + ",");
        System.out.println("  \"channel_active\": " + channelActive.get() + ",");
        System.out.println("  \"write_submitted\": " + writeSubmitted.get() + ",");
        System.out.println("  \"write_success\": " + writeSuccess.get() + ",");
        System.out.println("  \"read_observed\": " + readObserved.get() + ",");
        System.out.println("  \"bytes_written\": " + bytesWritten.get() + ",");
        System.out.println("  \"bytes_read\": " + bytesRead.get() + ",");
        System.out.println("  \"timeout_close\": " + timeoutClose.get() + ",");
        System.out.println("  \"exception_count\": " + exceptionCount.get() + ",");
        synchronized (exceptionLock) {
            System.out.println("  \"exception_classes\": \"" + String.join(",", exceptionClasses).replace("\"", "'") + "\",");
        }
        System.out.println("  \"duration_ms\": " + (finishedAt - startedAt));
        System.out.println("}");
    }
}
