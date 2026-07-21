const fs = require('fs').promises;
const path = require('path');

module.exports = (options) => {
    const outputDir = options.dir || 'reports';

    return {
        async results(results) {
            await fs.mkdir(outputDir, { recursive: true });

            const url = new URL(results.pageUrl);

            // Preserve query-string values.
            //
            // Example:
            // https://www.futureme.org/blog/category?name=goal-setting
            //
            // becomes:
            // www_futureme_org_blog_category_name_goal_setting
            const queryPart = url.search
                ? url.search
                    .replace(/^\?/, '')
                    .replace(/=/g, '/')
                : '';

            // Preserve URL fragments as well.
            //
            // Example:
            // https://www.marksandspencer.com/c/beauty
            //   #intid=gnav_LEVEL1_COMPONENT_beauty
            //
            // becomes:
            // www_marksandspencer_com_c_beauty
            //   _intid_gnav_level1_component_beauty
            const hashPart = url.hash
                ? url.hash
                    .replace(/^#/, '')
                    .replace(/=/g, '/')
                : '';

            const fullPath = [
                url.hostname,
                url.pathname,
                queryPart,
                hashPart
            ]
                .filter(Boolean)
                .join('/');

            // Replace dots, slashes, equals signs and other punctuation
            // with underscores, matching the report naming style used by
            // the other tools.
            const sanitizedBase = fullPath
                .replace(/[^a-z0-9]/gi, '_')
                .replace(/^_+|_+$/g, '')
                .toLowerCase();

            const fileName = `${sanitizedBase}.json`;
            const filePath = path.join(outputDir, fileName);

            await fs.writeFile(
                filePath,
                JSON.stringify(results, null, 2),
                'utf8'
            );

            console.log(`Report saved: ${filePath}`);
        }
    };
};