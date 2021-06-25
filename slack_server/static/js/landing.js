const $ = document.querySelector.bind(document)
document.querySelectorAll('.indicators li').forEach(el => {
    el.addEventListener('click', () => {
        const n = Number(el.dataset.slideTo)
        $(`.slide-${n}`).classList.remove('hide')
        $(`.slide-${(n + 1) % 2}`).classList.add('hide')
        $(`.indicators li:nth-child(${n + 1})`).classList.add('active')
        $(`.indicators li:nth-child(${((n + 1) % 2) + 1})`).classList.remove(
            'active'
        )
    })
})
