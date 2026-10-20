# v4 Commerce / RAG 데이터 계약

- `products`는 `id,name,brand,category,description,image_urls,specs`를 사용한다. 실제 DB 저장 시 `specs`는 `specs_json`에 매핑한다.
- `variants`는 `id,product_id,option_values,spec_overrides,unit_price_won,stock_qty`; 실물 옵션의 확인 결과가 아니라 **모의 시연용**임. DB에서는 `option_values_json`과 `spec_overrides_json`으로 매핑.
- `reviews`는 `id,product_id,variant_id,rating,body,source_kind,source_ref,written_at`이며 전부 `source_kind=SYNTHETIC`.
- `image_urls`는 원본 외부 CDN URL을 참조할 뿐 실물 이미지 사용 권한과 렌더링 성공을 보장하지 않음.
- `manufacturer_specs_verified=true`인 4개만 제조사 제품군 수준의 확인이 되어 있고, 나머지 `false`는 미확인.
- 상품별 실제 원본 후기 수, 플랫폼 전제 리뷰 수, 합성 리뷰 수는 세 가지 다른 개념. 직접 합산·치환하면 안 됨.
- 본 데이터의 플랫폼 전체 리뷰 수는 Commerce RAG의 `whole_count_verified`가 아니다. 시연 사이트 안의 20개 합성 후기만 `stored_review_count`로 인식하고 외부 구매자 경험처럼 보여주지 않아야 함.
- 본 패키지는 **수량 기준 완료 / 제조사 공식 스펙 및 실제 SKU 기준 미완료**.
- 평가셋은 검색색인에서 분리되어야 하며, 가상 후기를 실사용 근거처럼 인용하는 프롬프트는 차단해야 함.
