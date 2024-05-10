const path = require('path');

module.exports = {
    entry: './wagtail_fedit/static_src/global.ts',
    output: {
        'path': path.resolve(__dirname, 'wagtail_fedit/static/wagtail_fedit/js/'),
        'filename': 'edit.js'
    },
    resolve: {
        extensions: ['.ts', '...'],
    },
    mode: 'production',
    module: {
        rules: [
            {
                test: /\.css$/i,
                use: [
                    'style-loader', 'css-loader'
                ]
            },
            {
                test: /\.ts$/i,
                use: 'ts-loader',
                exclude: '/node_modules/'
            }
        ]
    }
}