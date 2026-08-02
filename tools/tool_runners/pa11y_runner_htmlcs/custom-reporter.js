const fs = require('fs').promises;
const path = require('path');

module.exports = (options) => {
    const outputDir = options.dir || 'reports';

    return {
        async results(results) {
            await fs.mkdir(outputDir, { recursive: true });

            const url = new URL(results.pageUrl);

            // Combine the URL components, ignoring the protocol (http/https)
            const fullPath = `${url.hostname}${url.pathname}${url.search}${url.hash}`;

            // 1. Replace any invalid characters (/, ?, =, #) with a dash
            // 2. Collapse multiple consecutive dashes into a single dash
            // 3. Remove leading or trailing dashes
            const sanitizedBase = fullPath
                .replace(/[^a-zA-Z0-9._-]+/g, '-')
                .replace(/-+/g, '-')
                .replace(/^-|-$/g, '');

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