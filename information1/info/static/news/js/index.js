var currentCid = 1; // 当前分类 id
var cur_page = 1; // 当前页
var total_page = 1;  // 总页数
var data_querying = false;   // 是否正在向后台获取数据,false:没有在加载数据 反之


$(function () {
    // 1.进入页面需要加载新闻列表数据
    updateNewsData()


    //2. 首页分类切换
    $('.menu li').click(function () {
        var clickCid = $(this).attr('data-cid')
        $('.menu li').each(function () {
            $(this).removeClass('active')
        })
        $(this).addClass('active')

        if (clickCid != currentCid) {
            // 记录当前分类id
            currentCid = clickCid

            // 重置分页参数
            cur_page = 1
            total_page = 1
            updateNewsData()
        }
    })

    //页面滚动加载相关
    $(window).scroll(function () {

        // 浏览器窗口高度
        var showHeight = $(window).height();

        // 整个网页的高度
        var pageHeight = $(document).height();

        // 页面可以滚动的距离
        var canScrollHeight = pageHeight - showHeight;

        // 页面滚动了多少,这个是随着页面滚动实时变化的
        var nowScroll = $(document).scrollTop();

        if ((canScrollHeight - nowScroll) < 100) {
            // TODO 判断页数，去更新新闻数据
            // 有触发多次的bug，使用标志位来限定请求次数
            // data_querying:false表示没有人在加载数据
            if(!data_querying){
                // 当前页数小于总页数才去加载数据
                if(cur_page <= total_page){
                    // 表示已经有人在加载了
                    data_querying = true
                    // 加载首页列表数据
                    updateNewsData()
                }else {
                    //页面超出范围不去加载数据
                    data_querying = false
                }


            }
        }
    })
})

function updateNewsData() {
    // TODO 更新新闻数据

    // 组织请求参数js对象
    params = {
        "cid": currentCid,
        "page": cur_page,
        "total_page": total_page
    }

    $.get("/news_list", params, function (resp) {

        if(resp){
            // 先清空原有数据
            if(cur_page == 1){
                 $(".list_con").html('')
            }
            // 数据加载完毕将改成false下次再下拉又可以去加载数据了。
            data_querying = false
            // 更新总页数
            total_page = resp.data.total_page
            // 页码自增
            cur_page += 1
            // 显示数据
            for (var i=0;i<resp.data.newsList.length;i++) {
                var news = resp.data.newsList[i]
                var content = '<li>'
                // 拼接url： /news/1
                content += '<a href="/news/'+ news.id + ' " class="news_pic fl"><img src="' + news.index_image_url + '?imageView2/1/w/170/h/170"></a>'
                content += '<a href="/news/'+ news.id +'" class="news_title fl">' + news.title + '</a>'
                content += '<a href="/news/'+ news.id +'" class="news_detail fl">' + news.digest + '</a>'
                content += '<div class="author_info fl">'
                content += '<div class="source fl">来源：' + news.source + '</div>'
                content += '<div class="time fl">' + news.create_time + '</div>'
                content += '</div>'
                content += '</li>'
                $(".list_con").append(content)
            }

        }


    })

}
