describe('Access all resources', () => {
	it('renders the main page ', () => {
		cy.visit('/')
	})

	it('fetch the catalog json file ', () => {
		cy.request('/api/data/catalog.json')
	})

	it('should navigate to the catalog page on click', () => {
		cy.contains('Catalogue').click()
		cy.location('pathname').should('eq', `/${URL_PREFIX}/catalogue`)
	})

	it('should navigate to the catalog item page on click', () => {
		cy.wait(3000)
		cy.contains(
			'Poverty Mapping Rollout Dataset for Timor Leste (2016)'
		).click()

		cy.location('pathname').should(
			'eq',
			`/${URL_PREFIX}/catalogue/povmap-timor-leste-rollout-dataset`
		)
	})

	it('should navigate to the main page', () => {
		cy.contains('AI4D Research Bank').click()
		cy.location('pathname').should('eq', `/${URL_PREFIX}/`)
	})
})
